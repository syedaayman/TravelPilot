import React, { useState } from 'react';
import { PlusCircle, CheckCircle2, AlertTriangle, Sparkles, X } from 'lucide-react';
import { Button } from '../common/Button';
import { validateActivity } from '../../api/trips';
import type { TripDetailResponse } from '../../types';

interface AddActivityModalProps {
  trip: TripDetailResponse;
  isOpen: boolean;
  onClose: () => void;
  onActivityAdded?: () => void;
}

export const AddActivityModal: React.FC<AddActivityModalProps> = ({ trip, isOpen, onClose, onActivityAdded }) => {
  const [dayNumber, setDayNumber] = useState<number>(1);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('Culture');
  const [startTime, setStartTime] = useState('18:00');
  const [durationMinutes, setDurationMinutes] = useState(90);
  const [cost, setCost] = useState(0);

  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const calculateEndTime = (start: string, durationMin: number) => {
    const [h, m] = start.split(':').map(Number);
    const totalMin = h * 60 + m + durationMin;
    const endH = Math.floor(totalMin / 60) % 24;
    const endM = totalMin % 60;
    return `${String(endH).padStart(2, '0')}:${String(endM).padStart(2, '0')}`;
  };

  const handleCheckFeasibility = async () => {
    if (!title.trim()) {
      setError('Please enter an activity title or landmark name.');
      return;
    }
    setError(null);
    setValidating(true);
    setValidationResult(null);

    const endTime = calculateEndTime(startTime, durationMinutes);

    try {
      const res = await validateActivity(trip.id, {
        day_number: Number(dayNumber),
        start_time: startTime,
        end_time: endTime,
        custom_title: title.trim(),
        duration_minutes: Number(durationMinutes),
      });
      setValidationResult(res);
    } catch (err: any) {
      setError(err.message || 'Validation request failed');
    } finally {
      setValidating(false);
    }
  };

  const applySuggestion = (s: any) => {
    setStartTime(s.start_time);
    const [sH, sM] = s.start_time.split(':').map(Number);
    const [eH, eM] = s.end_time.split(':').map(Number);
    const newDur = (eH * 60 + eM) - (sH * 60 + sM);
    if (newDur > 0) setDurationMinutes(newDur);
    setValidationResult(null);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white border border-slate-200 rounded-2xl max-w-lg w-full shadow-xl overflow-hidden animate-in fade-in duration-150">
        
        {/* Header */}
        <div className="p-5 border-b border-slate-200 flex justify-between items-center bg-slate-50">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <PlusCircle className="w-5 h-5 text-blue-600" />
              Add Feasibility-Checked Activity
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Deterministic engine verifies schedule buffers & operating hours before insertion.
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-xl font-bold px-2">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <div className="p-5 space-y-4">
          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-bold text-slate-600 block mb-1">Itinerary Day</label>
              <select
                value={dayNumber}
                onChange={e => {
                  setDayNumber(Number(e.target.value));
                  setValidationResult(null);
                }}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-blue-500"
              >
                {Array.from({ length: trip.duration_days || 1 }, (_, i) => i + 1).map(d => (
                  <option key={d} value={d}>Day {d}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-600 block mb-1">Category</label>
              <select
                value={category}
                onChange={e => setCategory(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-blue-500"
              >
                <option value="Culture">Culture & Arts</option>
                <option value="Textile">Textile / Craft Market</option>
                <option value="Food">Culinary / Dining</option>
                <option value="Heritage">Heritage & Architecture</option>
                <option value="Nature">Sunset / Scenic</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-600 block mb-1">Activity Title / Place Name</label>
            <input
              type="text"
              placeholder="e.g. Shilparamam Craft Village Evening Stroll"
              value={title}
              onChange={e => {
                setTitle(e.target.value);
                setValidationResult(null);
              }}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-bold text-slate-600 block mb-1">Start Time</label>
              <input
                type="time"
                value={startTime}
                onChange={e => {
                  setStartTime(e.target.value);
                  setValidationResult(null);
                }}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="text-xs font-bold text-slate-600 block mb-1">Duration (min)</label>
              <input
                type="number"
                min="15"
                step="15"
                value={durationMinutes}
                onChange={e => {
                  setDurationMinutes(Number(e.target.value));
                  setValidationResult(null);
                }}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="text-xs font-bold text-slate-600 block mb-1">Cost (₹)</label>
              <input
                type="number"
                min="0"
                value={cost}
                onChange={e => setCost(Number(e.target.value))}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Validation Result Box */}
          {validationResult && (
            <div className="space-y-2 pt-2">
              {validationResult.feasible ? (
                <div className="p-3.5 bg-blue-50 border border-blue-200 rounded-xl text-blue-900 text-xs space-y-1">
                  <div className="font-bold flex items-center gap-1.5 text-blue-700">
                    <CheckCircle2 className="w-4 h-4 text-blue-600" />
                    Feasible & Verified!
                  </div>
                  <p className="text-slate-700">
                    Fits cleanly into Day {dayNumber} schedule ({startTime} - {calculateEndTime(startTime, durationMinutes)}). No travel buffer or venue conflict detected.
                  </p>
                </div>
              ) : (
                <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs space-y-2">
                  <div className="font-bold flex items-center gap-1.5 text-rose-700">
                    <AlertTriangle className="w-4 h-4" />
                    Schedule Conflict Detected
                  </div>
                  <ul className="list-disc list-inside space-y-1 text-slate-700">
                    {(validationResult.issues || ['Proposed window conflicts with existing itinerary stops.']).map((iss: string, idx: number) => (
                      <li key={idx}>{iss}</li>
                    ))}
                  </ul>

                  {/* Suggestions */}
                  {validationResult.suggestions && validationResult.suggestions.length > 0 && (
                    <div className="pt-2 border-t border-rose-200">
                      <span className="font-semibold text-slate-800 block mb-1">Recommended Feasible Time Window:</span>
                      <div className="flex flex-wrap gap-2">
                        {validationResult.suggestions.map((s: any, idx: number) => (
                          <button
                            key={idx}
                            onClick={() => applySuggestion(s)}
                            className="px-2.5 py-1 bg-white border border-blue-200 rounded text-blue-700 hover:bg-blue-50 text-xs font-mono font-semibold"
                          >
                            {s.start_time} - {s.end_time} ({s.reason})
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-5 border-t border-slate-200 bg-slate-50 flex justify-between items-center">
          <Button variant="outline" onClick={onClose} className="border-slate-200 text-slate-600 hover:bg-slate-100">
            Cancel
          </Button>

          <Button
            onClick={() => {
              if (validationResult?.feasible) {
                if (onActivityAdded) onActivityAdded();
                onClose();
              } else {
                handleCheckFeasibility();
              }
            }}
            disabled={validating}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold flex items-center gap-2"
          >
            {validating ? (
              <>Checking Engine...</>
            ) : validationResult?.feasible ? (
              <>Confirmed & Added ✓</>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Check Feasibility
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};
