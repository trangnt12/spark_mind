

def test_viet_tat_haui_ra_ten_day_du():
    """HAUI (viết tắt trong cột viet_tat) phải đổi thành tên đầy đủ, ở mọi cấp học và cả khi nằm trong câu dài."""
    import pandas as pd
    from sparkmind.school_matching import them_cot_truong
    d = pd.DataFrame({"A3": ["HAUI", "dh công nghiệp hà nội - HaUI"], "cap_hoc": ["Không rõ", "Đại học"]})
    kq = them_cot_truong(d)
    assert set(kq["truong_chuan"]) == {"Trường Đại học Công nghiệp Hà Nội"}
