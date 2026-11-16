CURRENT = "v2"
LEGACY = "v1"


def rate_label(basis_points: int) -> str:
    whole = basis_points // 100
    frac = basis_points % 100
    return f"{whole}.{frac:02d}%"


def measure(beds: list[dict], protocol: str):
    sown = 0
    sprouted = 0
    moldy = 0
    for bed in beds:
        if bed["moldy"] > bed["sown"] or bed["sprouted"] > bed["sown"]:
            raise ValueError("某一床的霉粒或发芽数超过了播种数")
        if bed["sprouted"] + bed["moldy"] > bed["sown"]:
            raise ValueError("发芽数与霉粒数加在一起超过了播种数")
        sown += bed["sown"]
        sprouted += bed["sprouted"]
        moldy += bed["moldy"]
    if protocol == LEGACY:
        if sown <= 0:
            raise ValueError("旧口径的分母是零")
        basis = (sprouted * 10000) // sown
        return {
            "protocol_version": LEGACY,
            "tested": sown,
            "excluded_mold": 0,
            "sprouted": sprouted,
            "rate_bp": basis,
            "note": "旧口径把霉粒留在分母里",
        }
    tested = sown - moldy
    if tested <= 0:
        raise ValueError("剔除霉粒后没有可计种子")
    if sprouted > tested:
        raise ValueError("发芽数大于剔除霉粒后的分母")
    basis = (sprouted * 10000) // tested
    return {
        "protocol_version": CURRENT,
        "tested": tested,
        "excluded_mold": moldy,
        "sprouted": sprouted,
        "rate_bp": basis,
        "note": "现行口径的分母是播种粒数减去霉粒数",
    }
