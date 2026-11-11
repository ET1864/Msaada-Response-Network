from django.utils import timezone

from .models import ResourceOffer

# A request holds stock only once an organization has approved it.
RESERVING_STATUSES = {"Approved", "In Progress", "Fulfilled"}


class StockError(Exception):
    """Raised when an approval would take more stock than an offer has left."""


def available_offers():
    """Active, unexpired offers that still have stock."""
    return (
        ResourceOffer.objects
        .filter(status="Active", quantity_available__gt=0, valid_until__gt=timezone.now())
        .select_related("item")
        .order_by("item__category", "item__name")
    )


def sync_reservations(req):
    """Make the stock match the request's status.

    Approved, In Progress or Fulfilled: each requested item is taken out of its offer.
    Anything else (Pending, Under Review, Redirected): any stock taken is given back.
    Safe to call again and again.
    """
    should_reserve = req.status in RESERVING_STATUSES

    for line in req.lines.select_related("offer", "item"):
        offer = line.offer
        if offer is None:
            continue

        if should_reserve and not line.reserved:
            if not offer.is_valid():
                raise StockError(f"The offer for {line.item.name} is no longer active.")
            if offer.quantity_available < line.quantity:
                raise StockError(
                    f"Not enough {line.item.name}: {offer.quantity_available} {line.item.unit} left, "
                    f"{line.quantity} requested."
                )
            offer.quantity_available -= line.quantity
            if offer.quantity_available == 0:
                offer.status = "Exhausted"
            offer.save()
            line.reserved = True
            line.save()

        elif not should_reserve and line.reserved:
            offer.quantity_available += line.quantity
            if offer.status == "Exhausted":
                offer.status = "Active"
            offer.save()
            line.reserved = False
            line.save()
