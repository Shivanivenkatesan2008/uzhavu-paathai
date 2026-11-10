import heapq


class BuyerGraph:
    def __init__(self):
        # Graph using an adjacency list
        self.graph = {}

    def add_connection(self, crop_name, buyer):
        if crop_name not in self.graph:
            self.graph[crop_name] = []

        self.graph[crop_name].append(buyer)

    def get_buyers(self, crop_name):
        return self.graph.get(crop_name, [])

def build_buyer_index(buyers):
    buyer_index = {}

    for buyer in buyers:
        crop_name = str(buyer["crop_name"] or "").strip().lower()

        if crop_name not in buyer_index:
            buyer_index[crop_name] = []

        buyer_index[crop_name].append(dict(buyer))

    return buyer_index
def calculate_match_score(crop, buyer, farmer_district):
    score = 40
    reasons = ["Crop matched / பயிர் பொருந்துகிறது"]

    farmer_quantity = float(crop["quantity"])
    buyer_quantity = float(buyer["required_quantity"])

    # Quantity matching
    if buyer_quantity > 0:
        quantity_score = min(
            25,
            round(25 * farmer_quantity / buyer_quantity)
        )
        score += quantity_score

    # Quality matching
    farmer_quality = str(crop["quality"]).strip().lower()
    buyer_quality = str(buyer["quality"]).strip().lower()

    if farmer_quality and farmer_quality == buyer_quality:
        score += 20
        reasons.append("Quality matched / தரம் பொருந்துகிறது")

    # District matching
    if farmer_district.strip().lower() == buyer["district"].strip().lower():
        score += 15
        reasons.append("Same district / ஒரே மாவட்டம்")

    return min(score, 100), reasons


def find_best_buyers(crop, buyers, farmer_district):

    # 1. Dictionary – Index buyers by crop
    buyer_index = build_buyer_index(buyers)

    crop_name = str(crop["crop_name"] or "").strip().lower()

    matching_buyers = buyer_index.get(crop_name, [])

    # 2. Graph – Connect crop with matching buyers
    graph = BuyerGraph()

    for buyer in matching_buyers:
        graph.add_connection(crop_name, buyer)

    # 3. Priority Queue – Rank buyers by score
    priority_queue = []

    for buyer in graph.get_buyers(crop_name):

        score, reasons = calculate_match_score(
            crop, buyer, farmer_district
        )

        heapq.heappush(
            priority_queue,
            (-score, buyer["id"], buyer, reasons)
        )

    ranked_buyers = []

    while priority_queue:
        negative_score, buyer_id, buyer, reasons = heapq.heappop(
            priority_queue
        )

        ranked_buyers.append({
            "buyer": buyer,
            "score": -negative_score,
            "reasons": reasons
        })

    return ranked_buyers
def find_price_qualifying_buyers(buyers, expected_price):

    try:
        expected_price = float(expected_price)
    except (TypeError, ValueError):
        return []

    valid_buyers = []

    # Sort buyers by offered price
    for buyer in buyers:
        try:
            price = float(buyer["offered_price"])
        except (TypeError, ValueError,KeyError,IndexError):
            continue

        buyer_copy = dict(buyer)
        buyer_copy["_price_value"] = price
        valid_buyers.append(buyer_copy)

    valid_buyers.sort(key=lambda b: b["_price_value"])

    # Binary Search
    low = 0
    high = len(valid_buyers)

    while low < high:
        mid = (low + high) // 2

        if valid_buyers[mid]["_price_value"] < expected_price:
            low = mid + 1
        else:
            high = mid

    # Return buyers whose offers meet expected price
    result = []

    for buyer in valid_buyers[low:]:
        buyer.pop("_price_value")
        result.append(buyer)

    return result