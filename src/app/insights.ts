import type { OperationsState, ProactiveInsight } from "../types";
import { namesMatch } from "./format";

export function isActionableInsight(
  insight: ProactiveInsight,
  state: OperationsState,
): boolean {
  if (
    insight.color === "green" ||
    insight.actionType === "memory_insight_generated"
  ) {
    return false;
  }

  if (insight.actionType !== "create_supplier_order_draft") {
    return true;
  }

  const product = state.products.find(
    (candidate) =>
      namesMatch(insight.entityName, candidate.name) ||
      namesMatch(insight.title, candidate.name),
  );

  if (!product) {
    return false;
  }

  return state.inventoryAlerts.some(
    (alert) => !alert.resolved && alert.productId === product.id,
  );
}
