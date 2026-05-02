from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    DISPATCHER = "dispatcher"
    DRIVER = "driver"


class VehicleStatus(StrEnum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"


class JobStatus(StrEnum):
    PENDING = "pending"
    CALCULATING = "calculating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SolverAlgorithm(StrEnum):
    NEAREST_NEIGHBOR = "nearest_neighbor"
    GENETIC_ALGORITHM = "genetic_algorithm"
    CLARKE_WRIGHT_SAVINGS = "clarke_wright_savings"


class Objective(StrEnum):
    MINIMIZE_DISTANCE = "minimize_distance"
    MINIMIZE_TIME = "minimize_time"
    MINIMIZE_COST = "minimize_cost"


class RouteStatus(StrEnum):
    PLANNED = "planned"
    DISPATCHED = "dispatched"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class StopStatus(StrEnum):
    PENDING = "pending"
    EN_ROUTE = "en_route"
    ARRIVED = "arrived"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TrackingStatus(StrEnum):
    ON_TIME = "on_time"
    DELAYED = "delayed"
    OFF_ROUTE = "off_route"
