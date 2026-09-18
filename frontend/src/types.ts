export type Event = {
  id: string;
  title: string;
  description: string;
  category: string;
  category_name: string;
  tags: string[];
  image_url: string | null;
  image_credit: string | null;
  start_date: string;
  end_date: string;
  timezone: string;
  price_min: number | null;
  price_max: number | null;
  is_free: boolean;
  city: string;
  location_name: string;
  address: string;
  latitude: number | null;
  longitude: number | null;
  source_url: string | null;
  provider: string;
  reasons: string[];
};
export type Category = { id: string; name: string };
export type CatalogEvent = Event & { is_saved: boolean };
export type CatalogResult = {
  items: CatalogEvent[];
  total: number;
  has_more: boolean;
};
export type User = {
  id: string;
  first_name: string;
  city: string;
  onboarding_completed: boolean;
};
export type Preferences = {
  city: string;
  categories: string[];
  budget_max: number | null;
  companion: string;
  preferred_days: string;
  preferred_time: string;
};
export type Config = {
  demo_mode: boolean;
  event_provider: string;
  max_bot_name: string;
  demo_cities: string[];
};
declare global {
  interface Window {
    WebApp?: {
      initData: string;
      initDataUnsafe?: { start_param?: string };
      shareMaxContent?: (params: {
        text?: string;
        link?: string;
      }) => void | Promise<unknown>;
      BackButton?: {
        show(): void;
        hide(): void;
        onClick(cb: () => void): void;
        offClick(cb: () => void): void;
      };
    };
  }
}

export type EveningVibe =
  "active" | "calm" | "date" | "learn" | "culture" | "surprise";
export type EveningOptions = {
  vibe: EveningVibe;
  duration_hours: 2 | 4 | 6;
  budget_max: 0 | 1000 | 3000 | null;
};
export type EveningEvent = Event & {
  estimated_price: number | null;
  next_transfer: { distance_km: number; minutes: number } | null;
};
export type EveningPlan = EveningOptions & {
  id: string;
  saved: boolean;
  created_at: string;
  city: string;
  date: string;
  events: EveningEvent[];
  event_count: number;
  total_cost: number;
  cost_complete: boolean;
  duration_minutes: number;
  score: number;
  score_components: Record<string, number>;
  reasons: string[];
  warnings: string[];
};
export type EveningGeneration = {
  plan: EveningPlan | null;
  reason: "no_matches" | "exhausted" | null;
};
