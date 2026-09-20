import { Check, X, ArrowRight, IndianRupee, Clock, MapPin, AlertCircle, PlusCircle, Trash2, Edit3 } from 'lucide-react';
import { Button } from './Button';
import type { ProposedReplan, WhatIfSimulationResult, ItemModification } from '../../types';

interface ProposalReviewModalProps {
  proposal: ProposedReplan | WhatIfSimulationResult;
  type: 'replan' | 'simulation';
  onApply: (id: string, type: 'replan' | 'simulation') => void;
  onReject: (id: string, type: 'replan' | 'simulation') => void;
}

export function ProposalReviewModal({ proposal, type, onApply, onReject }: ProposalReviewModalProps) {
  const isSimulation = type === 'simulation';
  const id = isSimulation ? (proposal as WhatIfSimulationResult).simulation_id : (proposal as ProposedReplan).replan_id;
  
  const diff = proposal.diff;
  
  const formatMoney = (amount: number) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden border border-slate-200">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 text-slate-900 flex justify-between items-center">
          <div>
            <h2 className="text-lg font-bold flex items-center gap-2">
              {isSimulation ? 'Review What-If Simulation' : 'Review Disruption Replan'}
              {!proposal.feasible && <span className="bg-rose-100 border border-rose-200 text-rose-700 text-xs px-2.5 py-0.5 rounded-full flex items-center gap-1 font-semibold"><AlertCircle className="w-3 h-3"/> Infeasible</span>}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              {isSimulation 
                ? `Simulation Type: ${(proposal as WhatIfSimulationResult).type}`
                : `Disruption Handled: ${(proposal as ProposedReplan).disruption_type}`
              }
            </p>
          </div>
          <button onClick={() => onReject(id || '', type)} className="p-2 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-200/60 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-50 space-y-6">
          
          {/* Summary Banner */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-wrap gap-6 items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-50 border border-blue-100 rounded-xl text-blue-600">
                <IndianRupee className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs text-slate-500 font-bold uppercase tracking-wider mb-0.5">Budget Impact</p>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400 line-through text-xs font-mono">{formatMoney(diff.budget_before)}</span>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-lg font-bold font-mono text-slate-900">
                    {formatMoney(diff.budget_after)}
                  </span>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${diff.budget_delta <= 0 ? 'bg-blue-50 text-blue-700 border-blue-200' : 'bg-rose-50 text-rose-700 border-rose-200'}`}>
                    {diff.budget_delta > 0 ? '+' : ''}{formatMoney(diff.budget_delta)}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="text-right max-w-md">
              <p className="text-xs text-slate-500 font-bold uppercase tracking-wider mb-1">{isSimulation ? 'Simulation Summary' : 'Agent Replan Summary'}</p>
              <p className="text-xs font-medium text-slate-800 leading-relaxed">
                {isSimulation ? diff.summary : (proposal as ProposedReplan).summary || diff.summary}
              </p>
            </div>
          </div>

          {/* Validation Warnings */}
          {((proposal as any).warnings?.length > 0 || !(proposal as any).feasible) && (
            <div className="bg-rose-50 border border-rose-200 p-4 rounded-xl text-rose-800 text-xs space-y-1">
              <h4 className="flex items-center font-bold text-rose-900 mb-1">
                <AlertCircle className="w-4 h-4 mr-1.5 text-rose-600" />
                Validation Warnings
              </h4>
              <ul className="list-disc list-inside space-y-1 text-slate-700">
                {!(proposal as any).feasible && <li>The proposed itinerary is structurally invalid.</li>}
                {(proposal as any).warnings?.map((w: string, i: number) => <li key={i}>{w}</li>)}
                {(proposal as any).errors?.map((e: string, i: number) => <li key={i} className="text-rose-700">{e}</li>)}
              </ul>
            </div>
          )}

          {/* Diff Lists */}
          <div className="space-y-6">
            
            {/* Removed Items */}
            {(diff.removed_items || []).length > 0 && (
              <div>
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                  <Trash2 className="w-4 h-4 text-rose-600" /> Removed Activities
                </h4>
                <div className="grid gap-2.5">
                  {(diff.removed_items || []).map((item: any, i: number) => (
                    <div key={i} className="bg-white border border-slate-200 rounded-xl p-3.5 flex justify-between items-center shadow-sm">
                      <div>
                        <p className="font-bold text-xs text-slate-900 line-through">{item.custom_title || item.title || 'Activity'}</p>
                        <p className="text-[11px] text-slate-500">{item.scheduled_date} • {item.start_time} - {item.end_time}</p>
                      </div>
                      <span className="text-xs font-mono font-bold text-rose-600">-{formatMoney(item.cost)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Added Items */}
            {(diff.added_items || []).length > 0 && (
              <div>
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                  <PlusCircle className="w-4 h-4 text-blue-600" /> Added Alternatives
                </h4>
                <div className="grid gap-2.5">
                  {(diff.added_items || []).map((item: any, i: number) => (
                    <div key={i} className="bg-white border border-blue-200 rounded-xl p-3.5 flex justify-between items-center shadow-sm">
                      <div>
                        <p className="font-bold text-xs text-slate-900">{item.custom_title || item.title || 'Activity'}</p>
                        <p className="text-[11px] text-blue-700 font-medium flex items-center gap-1">
                          <Clock className="w-3 h-3 text-blue-600"/> {item.scheduled_date} • {item.start_time} - {item.end_time}
                        </p>
                      </div>
                      <span className="text-xs font-mono font-bold text-blue-700">+{formatMoney(item.cost)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Modified Items */}
            {(diff.modified_items || []).length > 0 && (
              <div>
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                  <Edit3 className="w-4 h-4 text-blue-600" /> Modified Items
                </h4>
                <div className="grid gap-2.5">
                  {(diff.modified_items || []).map((mod: ItemModification, i: number) => (
                    <div key={i} className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-sm">
                      <p className="font-bold text-xs text-slate-900 mb-2">{mod.title || 'Item Modified'}</p>
                      <div className="space-y-1">
                        {Object.entries(mod.field_changes).map(([field, change]) => (
                          <div key={field} className="text-xs flex items-center gap-2 text-slate-700">
                            <span className="font-medium capitalize text-slate-500 w-24">{field.replace('_', ' ')}:</span>
                            <span className="line-through text-slate-400">{String(change.before)}</span>
                            <ArrowRight className="w-3 h-3 text-slate-400" />
                            <span className="font-bold text-slate-900">{String(change.after)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Empty state */}
            {(diff.added_items || []).length === 0 && (diff.removed_items || []).length === 0 && (diff.modified_items || []).length === 0 && (
              <div className="text-center py-8 text-slate-500 bg-white rounded-xl border border-slate-200 text-xs">
                <MapPin className="w-6 h-6 mx-auto text-slate-400 mb-2" />
                <p className="font-semibold text-slate-800">No itinerary items were added, removed, or modified.</p>
                <p className="text-[11px] mt-0.5">Top-level budget or duration properties updated.</p>
              </div>
            )}

          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-slate-200 bg-white flex justify-end gap-3">
          <Button variant="outline" onClick={() => onReject(id || '', type)} className="border-slate-200 text-slate-700 hover:bg-slate-50 text-xs">
            Reject Changes
          </Button>
          <Button 
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs px-5"
            onClick={() => onApply(id || '', type)}
          >
            <Check className="w-4 h-4 mr-1.5" />
            Apply Changes
          </Button>
        </div>
      </div>
    </div>
  );
}
