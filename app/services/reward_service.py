import json
import os

# File lưu dữ liệu người dùng
DATA_FILE = "user_data.json"


class RewardService:
    def __init__(self):
        self.data = self.load_data()

    def load_data(self):
        if not os.path.exists(DATA_FILE):
            return {"exp": 0, "level": 1}
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"exp": 0, "level": 1}

    def save_data(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f)

    def get_exp(self):
        return self.data.get("exp", 0)

    def get_level(self):
        return self.data.get("level", 1)

    # Cộng điểm và kiểm tra lên cấp
    def add_exp(self, amount):
        self.data["exp"] += amount

        # Công thức: Cứ 100 XP là lên 1 cấp
        new_level = 1 + (self.data["exp"] // 100)

        leveled_up = new_level > self.data["level"]
        self.data["level"] = new_level

        self.save_data()
        return leveled_up


reward_service = RewardService()
