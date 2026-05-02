from app.models.optimization_job import OptimizationJob
from app.repositories.base import BaseRepository


class OptimizationJobRepository(BaseRepository[OptimizationJob]):
    model = OptimizationJob

    def list_by_project(self, project_id: str) -> list[OptimizationJob]:
        return (
            self.db.query(OptimizationJob)
            .filter(OptimizationJob.project_id == project_id)
            .order_by(OptimizationJob.created_at.desc())
            .all()
        )

    def list_ordered(self) -> list[OptimizationJob]:
        return (
            self.db.query(OptimizationJob)
            .order_by(OptimizationJob.created_at.desc())
            .all()
        )
