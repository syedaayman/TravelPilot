import React, { useState, useEffect } from 'react';
import { Compass, BookOpen, Utensils, Scissors, Sparkles, Music, ShoppingBag, X, MapPin } from 'lucide-react';
import { getDestinationCulture } from '../../api/destinations';

interface DiscoverDestinationModalProps {
  destinationIdOrName: string | null;
  onClose: () => void;
}

export const DiscoverDestinationModal: React.FC<DiscoverDestinationModalProps> = ({ destinationIdOrName, onClose }) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'food' | 'crafts' | 'arts'>('overview');

  useEffect(() => {
    if (!destinationIdOrName) return;
    setLoading(true);
    getDestinationCulture(destinationIdOrName)
      .then(res => setData(res))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, [destinationIdOrName]);

  if (!destinationIdOrName) return null;

  const culture = data?.culture || {};
  const destinationName = data?.destination_name || destinationIdOrName;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white border border-slate-200 rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-xl overflow-hidden animate-in fade-in duration-150">
        
        {/* Header */}
        <div className="p-6 border-b border-slate-200 flex justify-between items-center bg-slate-50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
              <Compass className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                Discover {destinationName}
              </h2>
              <p className="text-xs text-slate-500">
                Cultural Heritage, Textiles, Culinary Traditions & Local Bazaars
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 p-2 rounded-lg hover:bg-slate-200/60 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 bg-white px-6 gap-2">
          {[
            { id: 'overview', label: 'History & Heritage', icon: BookOpen },
            { id: 'food', label: 'Culinary Heritage', icon: Utensils },
            { id: 'crafts', label: 'Textiles & Crafts', icon: Scissors },
            { id: 'arts', label: 'Music, Dance & Bazaars', icon: Music },
          ].map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-3.5 px-4 text-xs font-bold border-b-2 flex items-center gap-2 transition-all ${
                  isActive
                    ? 'border-blue-600 text-blue-600 bg-blue-50/50'
                    : 'border-transparent text-slate-500 hover:text-slate-900'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-slate-700">
          {loading ? (
            <div className="py-16 text-center text-slate-500 animate-pulse text-xs font-medium">
              Extracting cultural knowledge graph for {destinationName}...
            </div>
          ) : (
            <>
              {activeTab === 'overview' && (
                <div className="space-y-6">
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                    <h3 className="text-xs font-bold text-blue-900 uppercase tracking-wider flex items-center gap-2">
                      <BookOpen className="w-4 h-4 text-blue-600" /> Historical Context
                    </h3>
                    <p className="text-xs text-slate-700 leading-relaxed">{culture.history_and_heritage?.summary}</p>
                  </div>

                  <div>
                    <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Key Architectural & Heritage Highlights</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {(culture.history_and_heritage?.key_attractions || []).map((att: any, idx: number) => (
                        <div key={idx} className="p-3 bg-white border border-slate-200 rounded-xl shadow-sm">
                          <span className="font-bold text-xs text-blue-800 block">{att.name}</span>
                          <span className="text-[10px] text-slate-500 uppercase tracking-wide font-mono block">{att.period}</span>
                          <p className="text-xs text-slate-600 mt-1">{att.significance}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'food' && (
                <div className="space-y-6">
                  <div className="p-4 bg-blue-50/60 border border-blue-200 rounded-xl space-y-2">
                    <h3 className="text-xs font-bold text-blue-900 uppercase tracking-wider flex items-center gap-2">
                      <Utensils className="w-4 h-4 text-blue-600" /> Gastronomic Heritage
                    </h3>
                    <p className="text-xs text-slate-700 leading-relaxed">{culture.food?.culinary_heritage}</p>
                  </div>

                  <div>
                    <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Signature Regional Dishes</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {(culture.food?.signature_dishes || []).map((dish: any, idx: number) => (
                        <div key={idx} className="p-3 bg-white border border-slate-200 rounded-xl shadow-sm">
                          <div className="flex justify-between items-start">
                            <span className="font-bold text-sm text-slate-900">{dish.name}</span>
                            {dish.spice_level && (
                              <span className="text-[10px] px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 font-medium">
                                {dish.spice_level}
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-slate-600 mt-1">{dish.description}</p>
                          {dish.best_place && (
                            <p className="text-[11px] text-blue-700 mt-2 font-semibold flex items-center gap-1">
                              <MapPin className="w-3 h-3 text-blue-600" /> Best at: {dish.best_place}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'crafts' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-xs font-bold text-blue-700 uppercase tracking-wider mb-3 flex items-center gap-2">
                      <Scissors className="w-4 h-4" /> Traditional Textiles & Weaving
                    </h3>
                    <div className="space-y-3">
                      {(culture.textiles_and_crafts?.textiles || []).map((item: any, idx: number) => (
                        <div key={idx} className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
                          <span className="font-bold text-sm text-slate-900">{item.name}</span>
                          <p className="text-xs text-slate-600">{item.description}</p>
                          {item.famous_hubs && (
                            <p className="text-[11px] text-blue-700 font-medium mt-1">Famous Hubs: {item.famous_hubs.join(', ')}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="text-xs font-bold text-blue-700 uppercase tracking-wider mb-3 flex items-center gap-2">
                      <Sparkles className="w-4 h-4" /> Master Artisan Crafts & Decorative Art
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {(culture.textiles_and_crafts?.crafts || []).map((craft: any, idx: number) => (
                        <div key={idx} className="p-3 bg-white border border-slate-200 rounded-xl shadow-sm space-y-1">
                          <span className="font-bold text-xs text-slate-900">{craft.name}</span>
                          <p className="text-xs text-slate-600">{craft.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'arts' && (
                <div className="space-y-6">
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                    <h3 className="text-xs font-bold text-blue-700 uppercase tracking-wider flex items-center gap-2">
                      <Music className="w-4 h-4 text-blue-600" /> Classical & Folk Performing Arts
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      <div>
                        <span className="text-slate-500 font-bold block">Dance Form:</span>
                        <span className="text-slate-900">{culture.performing_arts?.dance || 'Local traditional dance'}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 font-bold block">Music Tradition:</span>
                        <span className="text-slate-900">{culture.performing_arts?.music || 'Regional classical/folk'}</span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                      <ShoppingBag className="w-4 h-4 text-blue-600" /> Iconic Local Bazaars & Markets
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {(culture.markets_and_shopping || []).map((m: any, idx: number) => (
                        <div key={idx} className="p-3 bg-white border border-slate-200 rounded-xl shadow-sm">
                          <span className="font-bold text-xs text-slate-900">{m.name}</span>
                          <p className="text-[11px] text-slate-500 mt-0.5">{m.known_for}</p>
                          {m.best_time && <span className="text-[10px] text-blue-700 font-medium mt-1 block">Best time: {m.best_time}</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
