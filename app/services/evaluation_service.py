from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import EvaluationRecord, RecommendationSet
from app.schemas.evaluation import EvaluationAverages, EvaluationCreate, EvaluationSummary


class EvaluationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, payload: EvaluationCreate) -> EvaluationRecord:
        if self.session.get(RecommendationSet, payload.recommendation_set_id) is None:
            raise AppError(
                status_code=404, code="RECOMMENDATION_NOT_FOUND", message="推荐结果不存在"
            )
        record = EvaluationRecord(**payload.model_dump())
        self.session.add(record)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise AppError(
                status_code=409, code="EVALUATION_EXISTS", message="该测试者已评价此推荐"
            ) from exc
        return record

    def summary(self) -> EvaluationSummary:
        count = int(self.session.scalar(select(func.count(EvaluationRecord.id))) or 0)
        averages = self.session.execute(
            select(
                func.avg(EvaluationRecord.relevance_score),
                func.avg(EvaluationRecord.difficulty_score),
                func.avg(EvaluationRecord.reason_score),
                func.avg(EvaluationRecord.holding_score),
                func.avg(EvaluationRecord.satisfaction_score),
            )
        ).one()
        distributions = Counter(self.session.scalars(select(EvaluationRecord.satisfaction_score)))
        scenarios = Counter(self.session.scalars(select(EvaluationRecord.profile_scenario)))

        def value(index: int) -> float:
            return round(float(averages[index] or 0), 2)

        return EvaluationSummary(
            sample_size=count,
            averages=EvaluationAverages(
                relevance=value(0),
                difficulty=value(1),
                reason=value(2),
                holding=value(3),
                satisfaction=value(4),
            ),
            satisfaction_distribution={score: distributions.get(score, 0) for score in range(1, 6)},
            scenario_counts=dict(scenarios),
        )

    def list_records(self, limit: int, offset: int) -> list[EvaluationRecord]:
        return list(
            self.session.scalars(
                select(EvaluationRecord)
                .order_by(EvaluationRecord.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )
