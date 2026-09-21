import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/client';
import { FolderInput, FolderPlus, RefreshCw, Trash2, Play, CheckCircle2, AlertCircle } from 'lucide-react';

export default function IngestTab() {
  const [folders, setFolders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [folderPath, setFolderPath] = useState('data/sample_courses');
  const [department, setDepartment] = useState('Computer Science');
  const [semester, setSemester] = useState('1');
  const [course, setCourse] = useState('Data Structures');
  const [ocrMode, setOcrMode] = useState('auto');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const fetchFolders = async () => {
    setLoading(true);
    try {
      const data = await adminApi.ingest.getFolders();
      setFolders(data || []);
    } catch (err) {
      console.error('Failed to load watched folders:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFolders();
  }, []);

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!folderPath.trim()) return;
    setSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      await adminApi.ingest.registerFolder({
        path: folderPath.trim(),
        department: department.trim() || null,
        semester: semester.trim() || null,
        course: course.trim() || null,
        ocr_mode: ocrMode,
      });
      setSuccess('Directory successfully registered to ingestion pipeline.');
      fetchFolders();
    } catch (err) {
      setError(err.message || 'Failed to register directory.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id, path) => {
    if (!window.confirm(`Unregister folder watcher for '${path}'?`)) return;
    try {
      await adminApi.ingest.deleteFolder(id);
      fetchFolders();
    } catch (err) {
      alert(`Error deleting folder: ${err.message}`);
    }
  };

  const handleScan = async (id) => {
    try {
      await adminApi.ingest.scanFolder(id);
      alert('Manual scan triggered. Inspect progress in the Pipeline tab.');
    } catch (err) {
      alert(`Scan error: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Registration Card */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle space-y-4">
        <div className="flex items-center gap-2.5 pb-3 border-b border-[#EAEAEA]">
          <div className="w-8 h-8 rounded-xl bg-charcoal text-white flex items-center justify-center">
            <FolderPlus className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-charcoal">
              Register Directory Ingestion Watcher
            </h3>
            <p className="text-xs text-muted">
              Auto-scan local PDF, syllabus, and gazette files with automatic hierarchical path-tagging.
            </p>
          </div>
        </div>

        {error && (
          <div className="p-3 bg-pastel-red/60 border border-[#F5C2C7] rounded-xl flex items-start gap-2 text-pastel-redText text-xs">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div className="p-3 bg-pastel-green/60 border border-[#C3E6CB] rounded-xl flex items-center gap-2 text-pastel-greenText text-xs font-semibold">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{success}</span>
          </div>
        )}

        <form onSubmit={handleRegister} className="space-y-3.5">
          <div>
            <label className="block text-xs font-semibold text-charcoal mb-1">
              Directory Path <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={folderPath}
              onChange={(e) => setFolderPath(e.target.value)}
              placeholder="e.g. data/sample_courses or /mnt/mdu_gazettes"
              className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-mono font-medium text-charcoal"
            />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">Department</label>
              <input
                type="text"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                placeholder="e.g. Computer Science"
                className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">Semester</label>
              <input
                type="text"
                value={semester}
                onChange={(e) => setSemester(e.target.value)}
                placeholder="e.g. 1"
                className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">Course Name</label>
              <input
                type="text"
                value={course}
                onChange={(e) => setCourse(e.target.value)}
                placeholder="e.g. Data Structures"
                className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">OCR Engine</label>
              <select
                value={ocrMode}
                onChange={(e) => setOcrMode(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs"
              >
                <option value="auto">Auto (Text First, Fallback OCR)</option>
                <option value="force">Force Tesseract OCR</option>
                <option value="skip">Skip Scanned Images</option>
              </select>
            </div>
          </div>

          <div className="pt-2 flex justify-end">
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 bg-charcoal hover:bg-[#262626] text-white rounded-xl text-xs font-semibold transition disabled:opacity-50"
            >
              {submitting ? 'Registering...' : 'Register Directory Watcher'}
            </button>
          </div>
        </form>
      </div>

      {/* Watched Folders Table */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle overflow-hidden">
        <div className="px-6 py-4 border-b border-[#EAEAEA] flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted">
            Active Watched Directories ({folders.length})
          </h3>
          <button
            onClick={fetchFolders}
            className="text-xs text-muted hover:text-charcoal flex items-center gap-1"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#FBFBFA] border-b border-[#EAEAEA] text-[11px] font-semibold text-muted uppercase">
                <th className="py-3 px-6">Directory Path</th>
                <th className="py-3 px-6">Department</th>
                <th className="py-3 px-6">Semester</th>
                <th className="py-3 px-6">Course</th>
                <th className="py-3 px-6">Registered</th>
                <th className="py-3 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EAEAEA]">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-muted">
                    Loading folders...
                  </td>
                </tr>
              ) : folders.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-muted">
                    No watched directories registered.
                  </td>
                </tr>
              ) : (
                folders.map((f) => (
                  <tr key={f.id} className="hover:bg-slate-50">
                    <td className="py-3 px-6 font-mono font-medium text-charcoal">{f.path}</td>
                    <td className="py-3 px-6">{f.department || '—'}</td>
                    <td className="py-3 px-6">{f.semester || '—'}</td>
                    <td className="py-3 px-6">{f.course || '—'}</td>
                    <td className="py-3 px-6 text-muted font-mono text-[11px]">
                      {new Date(f.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-6 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        <button
                          onClick={() => handleScan(f.id)}
                          title="Trigger immediate scan"
                          className="p-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-100 transition"
                        >
                          <Play className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(f.id, f.path)}
                          title="Unregister folder"
                          className="p-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 transition"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
