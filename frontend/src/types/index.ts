export type Severity = 'critical' | 'high' | 'medium' | 'low';

export interface Issue {
  id: string;
  category: string;
  pattern_id: string;
  issue: string;
  location: string;
  severity: Severity;
  recommendation: string;
}

export interface Recommendation {
  issue_id: string;
  priority: number;
  recommendation: string;
  implementation_hint: string;
}

export interface Extraction {
  metadonnees: {
    nom_client: string | null;
    objet: string | null;
    objectifs: string[];
    orientations_technologiques: string[];
  };
  contraintes_projet: {
    date_limite_soumission: string | null;
    budget: string | null;
    caution_provisoire: string | null;
    delai_execution: string | null;
  };
  dossier_reponse: {
    administratif: string[];
    technique: string[];
    financier: string[];
  };
  references: string[];
  exigences: string[];
  modalites_paiement: string[];
}

export interface Summary {
  total_issues: number;
  by_severity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    total: number;
  };
  by_category: Record<string, number>;
  confidence_level: string;
}

export interface Statistics {
  total_issues: number;
  critical_percentage: number;
  high_percentage: number;
  issues_per_functionality: number;
}

export interface AnalysisReport {
  generated_at: string;
  filename: string;
  summary: Summary;
  extraction: Extraction;
  issues: Issue[];
  recommendations: Recommendation[];
  statistics: Statistics;
  confidence_score: number;
  processing_time_ms: number;
}

export interface AnalysisStatus {
  id: string;
  status: 'processing' | 'completed' | 'failed';
  filename?: string;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded';
  ollama: 'connected' | 'disconnected';
}

export interface FeedbackRequest {
  analysis_id: string;
  issue_id: string;
  is_valid: boolean;
  comment?: string;
}

export interface RawAnalysisResponse {
  status: string;
  result?: AnalysisReport;
  resume?: {
    total_problemes: number;
    critiques: number;
    eleves: number;
    moyens: number;
    faibles: number;
    confidence_score?: number;
  };
  problemes?: Array<{
    id: string;
    titre: string;
    categorie: string;
    severite: string;
    localisation?: string;
    recommendation?: string;
    description?: string;
  }>;
  extraction?: {
    metadonnees?: {
      nom_client?: string | null;
      objet?: string | null;
      objectifs?: string[];
      orientations_technologiques?: string[];
    };
    contraintes_projet?: {
      date_limite_soumission?: string | null;
      budget?: string | null;
      caution_provisoire?: string | null;
      delai_execution?: string | null;
    };
    dossier_reponse?: {
      administratif?: string[];
      technique?: string[];
      financier?: string[];
    };
    references?: string[];
    exigences?: string[];
    modalites_paiement?: string[];
  };
  generated_at?: string;
  processing_time_ms?: number;
}

export interface HistoryItem {
  id: string;
  filename: string;
  status: string;
  nom_client: string | null;
  objet: string | null;
  total_problemes: number;
  created_at: number;
}
