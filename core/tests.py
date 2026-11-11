from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Item, Request, RequestItem, ResourceOffer
from .services import StockError, sync_reservations


def make_offer(quantity=100):
    item = Item.objects.create(category="water", name="Drinking water", unit="litres")
    return ResourceOffer.objects.create(
        item=item, offered_by="Test Org", contact_phone="0700000000",
        quantity_available=quantity, location="Kisumu",
        valid_until=timezone.now() + timedelta(hours=72), status="Active",
    )


def make_request(offer, quantity, status="Pending"):
    req = Request.objects.create(
        submitted_by_name="Test Person", phone="0712345678", need_type="food_water",
        people_count=3, location="Kisumu", status=status,
    )
    RequestItem.objects.create(help_request=req, offer=offer, item=offer.item, quantity=quantity)
    return req


class ReferenceCodeTests(TestCase):
    def test_reference_code_is_generated_from_year_and_number(self):
        req = Request.objects.create(
            submitted_by_name="Test Person", phone="0712345678", need_type="shelter",
            people_count=2, location="Kisumu",
        )
        self.assertTrue(req.reference_code.startswith("MSA-"))
        self.assertTrue(req.reference_code.endswith(f"{req.pk:04d}"))


class StockReservationTests(TestCase):
    def test_approving_a_request_reserves_stock(self):
        offer = make_offer(100)
        req = make_request(offer, 30)
        req.status = "Approved"
        req.save()
        sync_reservations(req)
        offer.refresh_from_db()
        self.assertEqual(offer.quantity_available, 70)
        self.assertTrue(req.lines.get().reserved)

    def test_redirecting_an_approved_request_gives_stock_back(self):
        offer = make_offer(100)
        req = make_request(offer, 30)
        req.status = "Approved"
        req.save()
        sync_reservations(req)
        req.status = "Redirected"
        req.save()
        sync_reservations(req)
        offer.refresh_from_db()
        self.assertEqual(offer.quantity_available, 100)

    def test_cannot_approve_more_than_the_stock_left(self):
        offer = make_offer(10)
        req = make_request(offer, 30)
        req.status = "Approved"
        req.save()
        with self.assertRaises(StockError):
            sync_reservations(req)
        offer.refresh_from_db()
        self.assertEqual(offer.quantity_available, 10)

    def test_offer_is_marked_exhausted_when_stock_reaches_zero(self):
        offer = make_offer(50)
        req = make_request(offer, 50)
        req.status = "Approved"
        req.save()
        sync_reservations(req)
        offer.refresh_from_db()
        self.assertEqual(offer.status, "Exhausted")


class RequestFormTests(TestCase):
    def test_form_saves_chosen_items_and_sets_need_type(self):
        offer = make_offer(100)
        response = self.client.post(reverse("request_help"), {
            "submitted_by_name": "Test Person", "phone": "0712345678",
            "for_someone_else": "False", "people_count": "3", "location": "Kisumu",
            f"qty_{offer.pk}": "20",
        })
        self.assertEqual(response.status_code, 302)
        req = Request.objects.get()
        self.assertEqual(req.need_type, "food_water")
        self.assertEqual(req.lines.get().quantity, 20)

    def test_form_rejects_more_than_is_available(self):
        offer = make_offer(100)
        response = self.client.post(reverse("request_help"), {
            "submitted_by_name": "Test Person", "phone": "0712345678",
            "for_someone_else": "False", "people_count": "3", "location": "Kisumu",
            f"qty_{offer.pk}": "500",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Request.objects.count(), 0)


class AccessTests(TestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_organization_user_can_open_dashboard(self):
        user = User.objects.create_user("org1", password="a-long-test-password-1")
        user.groups.add(Group.objects.get_or_create(name="Organization")[0])
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_tracking_needs_the_matching_phone_number(self):
        req = make_request(make_offer(100), 10)
        wrong = self.client.get(reverse("track_request"), {"ref": req.reference_code, "phone": "0799999999"})
        self.assertNotContains(wrong, "result-card")
        right = self.client.get(reverse("track_request"), {"ref": req.reference_code, "phone": "0712 345 678"})
        self.assertContains(right, "result-card")
