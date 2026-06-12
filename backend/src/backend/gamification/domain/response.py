from pydantic import BaseModel


class GameScoreUpdateResponse(BaseModel):
    class_code: str
    points_earned: int
    base_points: int
    streak_bonus: int
    current_streak: int
    total_score: int
