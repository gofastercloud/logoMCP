export type JobPhase =
  | "queued"
  | "text_generation"
  | "image_generation"
  | "packaging"
  | "complete"
  | "error";

export interface BrandBrief {
  company_name: string;
  industry: string;
  target_audience: string;
  mood_keywords: string[];
  color_preferences?: string[] | null;
  description?: string | null;
}

export interface ColorEntry {
  hex: string;
  name: string;
  role: "primary" | "secondary" | "accent" | "neutral" | "background";
  rationale: string;
}

export interface TypographyRec {
  heading_font: string;
  body_font: string;
  rationale: string;
}

export interface AssetInfo {
  name: string;
  filename: string;
  width: number;
  height: number;
}

export interface CreativeDirection {
  visual_style: string;
  mood_description: string;
  logo_concepts: string[];
  brand_voice: string;
}

export interface GenerationResult {
  creative_direction: CreativeDirection;
  color_palette: ColorEntry[];
  typography: TypographyRec;
  assets: AssetInfo[];
  download_url: string;
}

export interface JobStatus {
  job_id: string;
  status: JobPhase;
  progress: number;
  current_step: string | null;
  result: GenerationResult | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProgressUpdate {
  type: "progress" | "preview" | "complete" | "error";
  phase?: JobPhase;
  step?: string;
  progress: number;
  message?: string;
  asset_name?: string;
}
