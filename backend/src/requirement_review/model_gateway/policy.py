"""Policy-aware dispatcher that selects local vs cloud per `data_policy`."""

from __future__ import annotations

from .errors import ModelGatewayConfigError


class PolicyModelGateway:
    """Routes a `review()` call to one of two injected gateways.

    - `local_only`            -> local gateway
    - `cloud_allowed`         -> cloud gateway
    - `cloud_redacted`        -> cloud gateway (the client itself redacts)
    """

    def __init__(self, *, local, cloud, default_data_policy=None):
        if local is None or cloud is None:
            raise ModelGatewayConfigError(
                "PolicyModelGateway requires both `local and `cloud` gateways"
            )
        self.local = local
        self.cloud = cloud
        self.default_data_policy = default_data_policy

    async def review(self, *, project_id, data_policy, dimension, requirement, knowledge):
        from requirement_review.domain.models import DataPolicy

        policy = data_policy or self.default_data_policy
        if policy is None:
            raise ModelGatewayConfigError(
                "data_policy is required (no default supplied)"
            )
        if policy == DataPolicy.LOCAL_ONLY:
            return await self.local.review(
                project_id=project_id,
                data_policy=policy,
                dimension=dimension,
                requirement=requirement,
                knowledge=knowledge,
            )
        if policy in (DataPolicy.CLOUD_ALLOWED, DataPolicy.CLOUD_REDACTED):
            return await self.cloud.review(
                project_id=project_id,
                data_policy=policy,
                dimension=dimension,
                requirement=requirement,
                knowledge=knowledge,
            )
        raise ModelGatewayConfigError(f"unsupported data_policy: {policy!r}")
