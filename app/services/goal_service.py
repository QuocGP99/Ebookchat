import json
import os
from datetime import datetime

DATA_FILE = "user_data.json"


class GoalService:
    def __init__(self):
        self.data = self.load_data()
        self.check_new_day()

    def load_data(self):
        default = {"date": "", "minutes_read": 0, "daily_goal": 30}
        if not os.path.exists(DATA_FILE):
            return default
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # QUAN TRỌNG: Kiểm tra xem file cũ có key "date" không
                if "date" not in data:
                    return default  # Reset nếu file cũ không tương thích
                return data
        except:
            return default

    def save_data(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f)

    def check_new_day(self):
        today = datetime.now().strftime("%Y-%m-%d")

        # Dùng .get() để an toàn hơn, tránh crash nếu file lỗi
        current_date = self.data.get("date", "")

        if current_date != today:
            self.data["date"] = today
            self.data["minutes_read"] = 0
            self.save_data()

    def add_time(self, minutes=1):
        self.check_new_day()
        self.data["minutes_read"] = self.data.get("minutes_read", 0) + minutes
        self.save_data()

    def get_progress(self):
        """Trả về tuple (đã đọc, mục tiêu)"""
        return self.data.get("minutes_read", 0), self.data.get("daily_goal", 30)


# Khởi tạo object
goal_service = GoalService()
