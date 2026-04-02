import { useState, useCallback } from 'react';
import { analysisApi } from './services/api';
import type { AnalysisReport, HealthStatus, AnalysisStatus } from './types';
import { 
  Upload, FileText, AlertTriangle, CheckCircle, 
  Loader2, RefreshCw, Send, ThumbsUp, ThumbsDown 
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
      const response = await analysisApi.analyzeText(textInput);
      const reportData = response.result || response;
      
      const transformedReport = {
        ...reportData,
        summary: {
          total_issues: reportData.resume?.total_problemes ?? 0,
          by_severity: {
            critical: reportData.resume?.critiques ?? 0,
            high: reportData.resume?.eleves ?? 0,
            medium: reportData.resume?.moyens ?? 0,
            low: reportData.resume?.faibles ?? 0,
          },
          by_category: {},
        },
        issues: (reportData.problemes ?? []).map((p: any) => ({
          id: p.id,
          issue: p.titre,
          category: p.categorie,
          severity: p.severite?.toLowerCase() ?? 'medium',
          location: p.localisation ?? '',
          recommendation: p.recommendation ?? '',
          description: p.description ?? '',
        })),
        extraction: {
          functionalities: reportData.extraction?.functionalites ?? [],
          actors: reportData.extraction?.acteurs ?? [],
          constraints: reportData.extraction?.contraintes ?? [],
          interfaces: reportData.extraction?.interfaces ?? [],
          data: reportData.extraction?.donnees ?? [],
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
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div>
                  <p className="text-gray-500 text-xs mb-2">Fonctionnalités</p>
                  <p className="text-xl font-semibold text-indigo-400">{report?.extraction?.functionalities?.length ?? 0}</p>
                </div>
                <div>
                  <p className="text-gray-500 text-xs mb-2">Acteurs</p>
                  <p className="text-xl font-semibold text-indigo-400">{report?.extraction?.actors?.length ?? 0}</p>
                </div>
                <div>
                  <p className="text-gray-500 text-xs mb-2">Contraintes</p>
                  <p className="text-xl font-semibold text-indigo-400">{report?.extraction?.constraints?.length ?? 0}</p>
                </div>
                <div>
                  <p className="text-gray-500 text-xs mb-2">Interfaces</p>
                  <p className="text-xl font-semibold text-indigo-400">{report?.extraction?.interfaces?.length ?? 0}</p>
                </div>
                <div>
                  <p className="text-gray-500 text-xs mb-2">Données</p>
                  <p className="text-xl font-semibold text-indigo-400">{report?.extraction?.data?.length ?? 0}</p>
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
    </div>
  );
}

export default App;
