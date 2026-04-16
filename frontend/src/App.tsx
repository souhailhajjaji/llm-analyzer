import { useState, useCallback, useEffect } from 'react';
import { analysisApi } from './services/api';
import type { AnalysisReport, HealthStatus, AnalysisStatus, HistoryItem } from './types';
import { 
  Upload, FileText, AlertTriangle, CheckCircle, 
  Loader2, RefreshCw, Send, ThumbsUp, ThumbsDown, History, Trash2
} from 'lucide-react';

function App() {
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [textInput, setTextInput] = useState('');
  const [activeTab, setActiveTab] = useState<'upload' | 'text'>('upload');
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);

  const checkHealth = useCallback(async () => {
    try {
      const status = await analysisApi.checkHealth();
      setHealth(status);
    } catch (err) {
      setHealth({ status: 'degraded', ollama: 'disconnected' });
    }
  }, []);

  useState(() => {
    checkHealth();
  });

  const loadHistory = useCallback(async () => {
    try {
      const data = await analysisApi.getAnalyses();
      setHistory(data.analyses || []);
    } catch (err) {
      console.error('Failed to load history', err);
    }
  }, []);

  const viewHistoryItem = async (id: string) => {
    try {
      const result = await analysisApi.getAnalysisResult(id);
      setReport(result as unknown as AnalysisReport);
      setShowHistory(false);
    } catch (err) {
      setError('Failed to load analysis');
    }
  };

  const deleteHistoryItem = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await analysisApi.deleteAnalysis(id);
      loadHistory();
    } catch (err) {
      setError('Failed to delete analysis');
    }
  };

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const handleFile = async (file: File) => {
    if (!file) return;
    
    setLoading(true);
    setError(null);
    setAnalyzing(true);
    
    try {
      const result = await analysisApi.analyzeFile(file);
      
      const pollResult = async () => {
        let status: AnalysisStatus;
        do {
          await new Promise(r => setTimeout(r, 1000));
          status = await analysisApi.getAnalysisStatus(result.id);
        } while (status.status === 'processing');
        
        if (status.status === 'completed') {
          const report = await analysisApi.getAnalysisResult(result.id);
          setReport(report);
        } else {
          setError('Analysis failed');
        }
        setAnalyzing(false);
      };
      
      pollResult();
    } catch (err) {
      setError('Failed to analyze file');
      setAnalyzing(false);
    } finally {
      setLoading(false);
    }
  };

  const handleTextSubmit = async () => {
    if (!textInput.trim()) return;
    
    setLoading(true);
    setError(null);
    setAnalyzing(true);
    
    try {
      const reportData = await analysisApi.analyzeText(textInput);
      
      const transformedReport: AnalysisReport = {
        ...reportData as unknown as AnalysisReport,
        summary: {
          total_issues: reportData.resume?.total_problemes ?? 0,
          by_severity: {
            critical: reportData.resume?.critiques ?? 0,
            high: reportData.resume?.eleves ?? 0,
            medium: reportData.resume?.moyens ?? 0,
            low: reportData.resume?.faibles ?? 0,
            total: 0,
          },
          by_category: {},
          confidence_level: 'medium',
        },
        issues: (reportData.problemes ?? []).map((p: any) => ({
          id: p.id,
          issue: p.titre,
          category: p.categorie,
          severity: p.severite?.toLowerCase() ?? 'medium',
          location: p.localisation ?? '',
          recommendation: p.recommendation ?? '',
          pattern_id: '',
        })),
        extraction: {
          metadonnees: {
            nom_client: reportData.extraction?.metadonnees?.nom_client ?? null,
            objet: reportData.extraction?.metadonnees?.objet ?? null,
            objectifs: reportData.extraction?.metadonnees?.objectifs ?? [],
            orientations_technologiques: reportData.extraction?.metadonnees?.orientations_technologiques ?? [],
          },
          contraintes_projet: {
            date_limite_soumission: reportData.extraction?.contraintes_projet?.date_limite_soumission ?? null,
            budget: reportData.extraction?.contraintes_projet?.budget ?? null,
            caution_provisoire: reportData.extraction?.contraintes_projet?.caution_provisoire ?? null,
            delai_execution: reportData.extraction?.contraintes_projet?.delai_execution ?? null,
          },
          dossier_reponse: {
            administratif: reportData.extraction?.dossier_reponse?.administratif ?? [],
            technique: reportData.extraction?.dossier_reponse?.technique ?? [],
            financier: reportData.extraction?.dossier_reponse?.financier ?? [],
          },
          references: reportData.extraction?.references ?? [],
          exigences: reportData.extraction?.exigences ?? [],
          modalites_paiement: reportData.extraction?.modalites_paiement ?? [],
        },
        recommendations: [],
        statistics: {
          total_issues: reportData.resume?.total_problemes ?? 0,
          critical_percentage: 0,
          high_percentage: 0,
          issues_per_functionality: 0,
        },
        confidence_score: reportData.resume?.confidence_score ?? 0.8,
        generated_at: reportData.generated_at ?? new Date().toISOString(),
        processing_time_ms: reportData.processing_time_ms ?? 0,
        filename: 'Text Input',
      };
      
      setReport(transformedReport);
    } catch (err) {
      setError('Failed to analyze text');
    } finally {
      setLoading(false);
      setAnalyzing(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-600';
      case 'high': return 'bg-orange-500';
      case 'medium': return 'bg-yellow-500';
      case 'low': return 'bg-blue-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileText className="w-8 h-8 text-indigo-400" />
            <h1 className="text-xl font-semibold">Cahier Charges Analyzer</h1>
          </div>
          <button
            onClick={checkHealth}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors text-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            {health ? (
              <span className={health.ollama === 'connected' ? 'text-green-400' : 'text-red-400'}>
                {health.ollama === 'connected' ? 'Connecté' : 'Déconnecté'}
              </span>
            ) : 'Vérifier'}
          </button>
          <button
            onClick={() => { setShowHistory(true); loadHistory(); }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors text-sm"
          >
            <History className="w-4 h-4" />
            Historique
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {!report && (
          <div className="space-y-6">
            <div className="flex gap-4 mb-6">
              <button
                onClick={() => setActiveTab('upload')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  activeTab === 'upload' 
                    ? 'bg-indigo-600 text-white' 
                    : 'bg-gray-800 text-gray-400 hover:text-white'
                }`}
              >
                <Upload className="w-4 h-4 inline mr-2" />
                Importer un fichier
              </button>
              <button
                onClick={() => setActiveTab('text')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  activeTab === 'text' 
                    ? 'bg-indigo-600 text-white' 
                    : 'bg-gray-800 text-gray-400 hover:text-white'
                }`}
              >
                <FileText className="w-4 h-4 inline mr-2" />
                Saisir le texte
              </button>
            </div>

            {activeTab === 'upload' ? (
              <div
                onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
                onDragLeave={() => setDragActive(false)}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors ${
                  dragActive 
                    ? 'border-indigo-500 bg-indigo-500/10' 
                    : 'border-gray-700 hover:border-gray-600'
                }`}
              >
                <Upload className="w-12 h-12 mx-auto mb-4 text-gray-500" />
                <p className="text-lg mb-2">Glissez-déposez votre cahier des charges</p>
                <p className="text-gray-500 text-sm mb-4">ou</p>
                <label className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg cursor-pointer transition-colors">
                  <input
                    type="file"
                    accept=".pdf,.docx,.txt"
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
                    className="hidden"
                  />
                  Parcourir
                </label>
              </div>
            ) : (
              <div className="space-y-4">
                <textarea
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  placeholder="Collez le contenu de votre cahier des charges ici..."
                  className="w-full h-64 bg-gray-900 border border-gray-700 rounded-xl p-4 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none resize-none"
                />
                <button
                  onClick={handleTextSubmit}
                  disabled={loading || !textInput.trim()}
                  className="flex items-center gap-2 px-6 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  Analyser
                </button>
              </div>
            )}
          </div>
        )}

        {analyzing && (
          <div className="flex flex-col items-center justify-center py-16">
            <Loader2 className="w-12 h-12 text-indigo-500 animate-spin mb-4" />
            <p className="text-lg">Analyse en cours...</p>
            <p className="text-gray-500 text-sm">Cela peut prendre quelques secondes</p>
          </div>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/50 rounded-xl p-4 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {report && !analyzing && (
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-semibold">{report.filename || 'Analyse terminée'}</h2>
                <p className="text-gray-500 text-sm">
                  {new Date(report.generated_at).toLocaleString('fr-FR')} • 
                  Confidence: {Math.round(report.confidence_score * 100)}% • 
                  Temps: {report.processing_time_ms}ms
                </p>
              </div>
              <button
                onClick={() => { setReport(null); setTextInput(''); }}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
              >
               Nouvelle analyse
              </button>
            </div>

            <div className="grid grid-cols-4 gap-4">
              <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <p className="text-gray-500 text-sm mb-1">Total problèmes</p>
                <p className="text-3xl font-bold">{report?.summary?.total_issues ?? 0}</p>
              </div>
              <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <p className="text-gray-500 text-sm mb-1">Critiques</p>
                <p className="text-3xl font-bold text-red-500">{report?.summary?.by_severity?.critical ?? 0}</p>
              </div>
              <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <p className="text-gray-500 text-sm mb-1">Élevés</p>
                <p className="text-3xl font-bold text-orange-500">{report?.summary?.by_severity?.high ?? 0}</p>
              </div>
              <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <p className="text-gray-500 text-sm mb-1">Moyens</p>
                <p className="text-3xl font-bold text-yellow-500">{report?.summary?.by_severity?.medium ?? 0}</p>
              </div>
            </div>

            <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
              <h3 className="text-lg font-semibold mb-4">Extraction des éléments</h3>
              
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <p className="text-gray-500 text-xs mb-2 font-medium">Métadonnées</p>
                  {report?.extraction?.metadonnees?.nom_client && (
                    <p className="text-sm"><span className="text-gray-400">Client:</span> {report.extraction.metadonnees.nom_client}</p>
                  )}
                  {report?.extraction?.metadonnees?.objet && (
                    <p className="text-sm"><span className="text-gray-400">Objet:</span> {report.extraction.metadonnees.objet}</p>
                  )}
                  {report?.extraction?.metadonnees?.objectifs?.length > 0 && (
                    <div className="mt-2">
                      <p className="text-gray-500 text-xs">Objectifs:</p>
                      <ul className="text-sm list-disc list-inside">
                        {report.extraction.metadonnees.objectifs.map((o, i) => <li key={i}>{o}</li>)}
                      </ul>
                    </div>
                  )}
                  {report?.extraction?.metadonnees?.orientations_technologiques?.length > 0 && (
                    <div className="mt-2">
                      <p className="text-gray-500 text-xs">Orientations technologiques:</p>
                      <ul className="text-sm list-disc list-inside">
                        {report.extraction.metadonnees.orientations_technologiques.map((t, i) => <li key={i}>{t}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
                
                <div>
                  <p className="text-gray-500 text-xs mb-2 font-medium">Contraintes Projet</p>
                  {report?.extraction?.contraintes_projet?.date_limite_soumission && (
                    <p className="text-sm"><span className="text-gray-400">Date limite:</span> {report.extraction.contraintes_projet.date_limite_soumission}</p>
                  )}
                  {report?.extraction?.contraintes_projet?.budget && (
                    <p className="text-sm"><span className="text-gray-400">Budget:</span> {report.extraction.contraintes_projet.budget}</p>
                  )}
                  {report?.extraction?.contraintes_projet?.caution_provisoire && (
                    <p className="text-sm"><span className="text-gray-400">Caution:</span> {report.extraction.contraintes_projet.caution_provisoire}</p>
                  )}
                  {report?.extraction?.contraintes_projet?.delai_execution && (
                    <p className="text-sm"><span className="text-gray-400">Délai:</span> {report.extraction.contraintes_projet.delai_execution}</p>
                  )}
                </div>
              </div>
              
              {(report?.extraction?.dossier_reponse?.administratif?.length > 0 || 
                report?.extraction?.dossier_reponse?.technique?.length > 0 || 
                report?.extraction?.dossier_reponse?.financier?.length > 0) && (
                <div className="mt-4 pt-4 border-t border-gray-800">
                  <p className="text-gray-500 text-xs mb-2 font-medium">Dossier de Réponse</p>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-xs text-gray-400">Administratif:</p>
                      <ul className="text-sm list-disc list-inside">
                        {report?.extraction?.dossier_reponse?.administratif?.map((a, i) => <li key={i}>{a}</li>)}
                      </ul>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Technique:</p>
                      <ul className="text-sm list-disc list-inside">
                        {report?.extraction?.dossier_reponse?.technique?.map((t, i) => <li key={i}>{t}</li>)}
                      </ul>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Financier:</p>
                      <ul className="text-sm list-disc list-inside">
                        {report?.extraction?.dossier_reponse?.financier?.map((f, i) => <li key={i}>{f}</li>)}
                      </ul>
                    </div>
                  </div>
                </div>
              )}
              
              <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-gray-800">
                <div>
                  <p className="text-gray-500 text-xs mb-2">Références</p>
                  <p className="text-xl font-semibold text-indigo-400">{report?.extraction?.references?.length ?? 0}</p>
                </div>
                <div>
                  <p className="text-gray-500 text-xs mb-2">Exigences</p>
                  <p className="text-xl font-semibold text-indigo-400">{report?.extraction?.exigences?.length ?? 0}</p>
                </div>
                <div>
                  <p className="text-gray-500 text-xs mb-2">Modalités Paiement</p>
                  <p className="text-xl font-semibold text-indigo-400">{report?.extraction?.modalites_paiement?.length ?? 0}</p>
                </div>
              </div>
            </div>

            {report?.issues?.length > 0 && (
              <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
                <div className="p-4 border-b border-gray-800">
                  <h3 className="text-lg font-semibold">Problèmes détectés ({report?.issues?.length ?? 0})</h3>
                </div>
                <div className="divide-y divide-gray-800">
                  {report?.issues?.map((issue) => (
                    <div key={issue.id} className="p-4 flex items-start gap-4">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getSeverityColor(issue.severity)} text-white`}>
                        {issue.severity}
                      </span>
                      <div className="flex-1">
                        <p className="font-medium">{issue.issue}</p>
                        <p className="text-gray-500 text-sm">{issue.category} • {issue.location}</p>
                        <p className="text-gray-400 text-sm mt-1">{issue.recommendation}</p>
                      </div>
                      <div className="flex gap-2">
                        <button className="p-1 hover:text-green-500 transition-colors">
                          <ThumbsUp className="w-4 h-4" />
                        </button>
                        <button className="p-1 hover:text-red-500 transition-colors">
                          <ThumbsDown className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {report && report.issues?.length === 0 && (
              <div className="bg-green-500/10 border border-green-500/50 rounded-xl p-6 flex items-center gap-4">
                <CheckCircle className="w-8 h-8 text-green-500" />
                <div>
                  <p className="font-semibold text-green-400">Aucun problème détecté</p>
                  <p className="text-gray-400 text-sm">Votre cahier des charges semble complet et bien structuré.</p>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {showHistory && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 rounded-xl border border-gray-800 w-full max-w-3xl max-h-[80vh] overflow-hidden">
            <div className="p-4 border-b border-gray-800 flex items-center justify-between">
              <h2 className="text-xl font-semibold">Historique des analyses</h2>
              <button
                onClick={() => setShowHistory(false)}
                className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
              >
                ✕
              </button>
            </div>
            <div className="overflow-auto max-h-[calc(80vh-80px)]">
              {history.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  Aucune analyse dans l'historique
                </div>
              ) : (
                <table className="w-full">
                  <thead className="bg-gray-800/50 sticky top-0">
                    <tr>
                      <th className="text-left p-3 text-sm font-medium text-gray-400">Date</th>
                      <th className="text-left p-3 text-sm font-medium text-gray-400">Client</th>
                      <th className="text-left p-3 text-sm font-medium text-gray-400">Objet</th>
                      <th className="text-left p-3 text-sm font-medium text-gray-400">Problèmes</th>
                      <th className="text-left p-3 text-sm font-medium text-gray-400">Statut</th>
                      <th className="p-3"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800">
                    {history.map((item) => (
                      <tr
                        key={item.id}
                        onClick={() => viewHistoryItem(item.id)}
                        className="hover:bg-gray-800/50 cursor-pointer transition-colors"
                      >
                        <td className="p-3 text-sm">
                          {item.created_at ? new Date(item.created_at * 1000).toLocaleString('fr-FR') : '-'}
                        </td>
                        <td className="p-3 text-sm">{item.nom_client || '-'}</td>
                        <td className="p-3 text-sm max-w-xs truncate">{item.objet || '-'}</td>
                        <td className="p-3 text-sm">
                          <span className={`px-2 py-1 rounded text-xs ${
                            item.total_problemes === 0 ? 'bg-green-500/20 text-green-400' :
                            item.total_problemes > 5 ? 'bg-red-500/20 text-red-400' :
                            'bg-yellow-500/20 text-yellow-400'
                          }`}>
                            {item.total_problemes}
                          </span>
                        </td>
                        <td className="p-3 text-sm">
                          <span className={`px-2 py-1 rounded text-xs ${
                            item.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                            item.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                            'bg-yellow-500/20 text-yellow-400'
                          }`}>
                            {item.status}
                          </span>
                        </td>
                        <td className="p-3">
                          <button
                            onClick={(e) => deleteHistoryItem(item.id, e)}
                            className="p-1 hover:text-red-400 transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
