

def test_viet_tat_phai_khop_cap():
    """HAUI là Đại học Công nghiệp Hà Nội với sinh viên; học sinh THPT ghi HAUI thì KHÔNG được gán trường đại học."""
    import pandas as pd
    from sparkmind.school_matching import them_cot_truong
    d = pd.DataFrame({"A3": ["HAUI", "dh công nghiệp hà nội - HaUI", "HAUI"],
                      "cap_hoc": ["Đại học", "Đại học", "THPT"]})
    kq = them_cot_truong(d)
    dh = "Trường Đại học Công nghiệp Hà Nội"
    assert list(kq["truong_chuan"][:2]) == [dh, dh]
    assert kq["truong_chuan"][2] != dh
