export type HeatPoint = {
  component: string;
  intensity: number;
  position: number[];
};

export type GoldenRecord = {
  sku_id: string;
  name: string;
  health_index: number;
  nrv_value: number;
  nrv_pct_msrp: number;
  recommended_action: string;
  routing: {
    target_hub: string;
    hub_id?: string;
    capacity_status: string;
    savings_via_clustering: number;
    consolidated_collection?: boolean;
    route_start?: { lat: number; lon: number };
    route_end?: { lat: number; lon: number };
    estimated_route_cost?: number;
  };
  ai_summary: string;
  condition_grade: string;
  sentiment_score: number;
  key_issues: string[];
  financial_justification: string;
  digital_twin: {
    top_failure_component: string;
    physical_entities: string[];
    failure_modes: string[];
    heatmap_coordinates: HeatPoint[];
  };
};

export type DispositionResponse = {
  records: GoldenRecord[];
  profit_recovery: { total_recovered_value: number; total_lost_value: number };
  stress_wms_active: boolean;
};

export async function fetchDisposition(stressWms: boolean): Promise<DispositionResponse> {
  const q = stressWms ? "?stress_wms=true" : "";
  const res = await fetch(`/disposition_insights${q}`);
  if (!res.ok) throw new Error("Failed to load disposition insights");
  return res.json();
}

export type NetworkMapResponse = {
  nodes: { id: string; label: string; lat: number; lon: number; capacity_pct: number }[];
  edges: {
    sku_id: string;
    hub: string;
    hub_id?: string;
    from?: { lat: number; lon: number };
    to?: { lat: number; lon: number };
    action?: string;
  }[];
  stress_wms_active: boolean;
};

export async function fetchNetworkMap(stressWms: boolean): Promise<NetworkMapResponse> {
  const q = stressWms ? "?stress_wms=true" : "";
  const res = await fetch(`/api/network_map${q}`);
  if (!res.ok) throw new Error("Failed to load network map");
  return res.json();
}
