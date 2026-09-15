import { useMemo } from "react";
import { RequirementReviewClient } from "../api/client";

export function useClient(): RequirementReviewClient {
  return useMemo(() => new RequirementReviewClient(), []);
}
