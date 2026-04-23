export type RiskLot = {
  source: string;
  lot_number: string;
  sale_date: string | null;
  hammer_price_usd: number | null;
  status: string | null;
  location: string | null;
  images: Array<{ image_url: string }>;
  price_events: Array<{ event_type: string; old_value: string | null; new_value: string; event_time: string }>;
};

export type RiskVehicle = {
  vin: string;
  make: string | null;
  model: string | null;
  year: number | null;
  title_brand: string | null;
  lots: RiskLot[];
};

export type RiskReasonKey =
  | "title"
  | "status"
  | "multipleRuns"
  | "priceRunup"
  | "missingImages"
  | "highBid";

export type RiskAssessment = {
  score: number;
  level: "low" | "medium" | "high";
  reasons: RiskReasonKey[];
};

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function assessVehicleRisk(vehicle: RiskVehicle | null, activeLot: RiskLot | null): RiskAssessment | null {
  if (!vehicle) return null;

  let score = 12;
  const reasons: RiskReasonKey[] = [];
  const title = (vehicle.title_brand || "").toLowerCase();
  const status = (activeLot?.status || "").toLowerCase();
  const imageCount = activeLot?.images?.length || 0;
  const lots = vehicle.lots || [];
  const bidNow = activeLot?.hammer_price_usd || 0;
  const soldPrices = lots.map((lot) => lot.hammer_price_usd).filter((value): value is number => value !== null);
  const averageBid =
    soldPrices.length > 0 ? soldPrices.reduce((sum, value) => sum + value, 0) / soldPrices.length : null;
  const hasRunup =
    activeLot?.price_events?.some((event) => {
      const type = event.event_type.toLowerCase();
      return type.includes("bid") || type.includes("price") || type.includes("sale");
    }) || false;

  if (title.includes("salvage") || title.includes("rebuilt") || title.includes("junk") || title.includes("parts")) {
    score += 18;
    reasons.push("title");
  }

  if (
    status.includes("sold") ||
    status.includes("on approval") ||
    status.includes("minimum bid") ||
    status.includes("run and drive") === false
  ) {
    score += 8;
    reasons.push("status");
  }

  if (lots.length >= 3) {
    score += 14;
    reasons.push("multipleRuns");
  }

  if (hasRunup && activeLot?.price_events && activeLot.price_events.length >= 3) {
    score += 8;
    reasons.push("priceRunup");
  }

  if (imageCount < 3) {
    score += 14;
    reasons.push("missingImages");
  }

  if (averageBid !== null && bidNow > averageBid * 1.18) {
    score += 16;
    reasons.push("highBid");
  }

  const finalScore = clamp(score, 0, 100);
  const level = finalScore >= 60 ? "high" : finalScore >= 35 ? "medium" : "low";

  return { score: finalScore, level, reasons };
}
