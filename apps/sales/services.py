from decimal import Decimal

from apps.core.utils import HUNDRED, quantize_ugx

HAIRCUT_20000_RATE = Decimal("20.00")
HAIRCUT_15000_RATE = Decimal("13.33")


def calculate_commission(employee, amount: Decimal) -> Decimal:
    if hasattr(employee, "calculate_commission"):
        return employee.calculate_commission(amount)
    return quantize_ugx(Decimal("0"))


def is_haircut_service(service) -> bool:
    name = (getattr(service, "name", "") or "").lower()
    return "haircut" in name or "hair cut" in name or "fade" in name


def haircut_commission_rate_for_price(service, price: Decimal):
    if not is_haircut_service(service):
        return None
    amount = int(quantize_ugx(price or Decimal("0")))
    if amount == 20000:
        return HAIRCUT_20000_RATE
    if amount == 15000:
        return HAIRCUT_15000_RATE
    return None


def commission_from_rate(amount: Decimal, rate: Decimal) -> Decimal:
    return quantize_ugx((amount * rate) / HUNDRED)


def allocate_weighted_amounts(entries, total_amount: Decimal | None, get_weight):
    entry_list = list(entries)
    if not entry_list:
        return []

    target_total = quantize_ugx(total_amount if total_amount is not None else Decimal("0"))
    target_total_int = int(target_total)

    if len(entry_list) == 1:
        return [(entry_list[0], target_total)]

    weights = [quantize_ugx(get_weight(entry) or Decimal("0")) for entry in entry_list]
    weight_total = sum(weights, Decimal("0"))

    allocations = []
    running_total = 0

    if weight_total > 0:
        weight_total_int = int(weight_total)
        for entry, weight in zip(entry_list[:-1], weights[:-1]):
            share = (target_total_int * int(weight)) // weight_total_int
            allocations.append((entry, Decimal(share)))
            running_total += share
    else:
        even_share = target_total_int // len(entry_list)
        for entry in entry_list[:-1]:
            allocations.append((entry, Decimal(even_share)))
            running_total += even_share

    allocations.append((entry_list[-1], Decimal(target_total_int - running_total)))
    return allocations


def allocate_service_amounts(services, total_amount: Decimal | None = None):
    service_list = list(services)
    base_total = sum((service.price for service in service_list), Decimal("0"))
    return allocate_weighted_amounts(
        service_list,
        total_amount if total_amount is not None else base_total,
        lambda service: service.price,
    )


def allocate_item_commissions(items, total_commission: Decimal | None = None):
    return allocate_weighted_amounts(items, total_commission, lambda item: item.price)
