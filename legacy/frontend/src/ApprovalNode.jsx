import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { 
  Building2, 
  Flame, 
  Leaf, 
  Zap, 
  Droplets, 
  Coins, 
  FileCheck2, 
  Clock, 
  AlertCircle
} from 'lucide-react';

const categoryThemes = {
  environment: {
    icon: Leaf,
    barBg: 'bg-emerald-500',
    iconBg: 'bg-emerald-100/70 text-emerald-700',
  },
  factory: {
    icon: Building2,
    barBg: 'bg-blue-500',
    iconBg: 'bg-blue-100/70 text-blue-700',
  },
  fire: {
    icon: Flame,
    barBg: 'bg-amber-500',
    iconBg: 'bg-amber-100/70 text-amber-700',
  },
  building: {
    icon: Building2,
    barBg: 'bg-indigo-500',
    iconBg: 'bg-indigo-100/70 text-indigo-700',
  },
  electrical: {
    icon: Zap,
    barBg: 'bg-amber-500',
    iconBg: 'bg-amber-100/70 text-amber-700',
  },
  water: {
    icon: Droplets,
    barBg: 'bg-cyan-500',
    iconBg: 'bg-cyan-100/70 text-cyan-700',
  },
  incentive: {
    icon: Coins,
    barBg: 'bg-purple-500',
    iconBg: 'bg-purple-100/70 text-purple-700',
  },
  general: {
    icon: FileCheck2,
    barBg: 'bg-slate-500',
    iconBg: 'bg-slate-100/70 text-slate-700',
  }
};

function ApprovalNode({ data, selected, targetPosition = Position.Top, sourcePosition = Position.Bottom }) {
  const categoryKey = (data.category || 'general').toLowerCase();
  const theme = categoryThemes[categoryKey] || categoryThemes.general;
  const CategoryIcon = theme.icon || FileCheck2;

  return (
    <div className="relative group flex flex-col items-center">
      {/* Target Connection Handle */}
      <Handle
        type="target"
        position={targetPosition}
        id="target"
      />

      {/* Card Body matching exact reference design */}
      <div 
        className={`w-[350px] bg-white rounded-2xl border transition-all duration-150 cursor-pointer overflow-hidden shadow-2xs ${
          selected 
            ? 'border-emerald-600 ring-4 ring-emerald-500/15 shadow-md scale-[1.01]' 
            : 'border-slate-200 hover:border-slate-300 hover:shadow-md'
        }`}
      >
        {/* Colour-coded top bar according to clearance category */}
        <div className={`h-2.5 w-full ${theme.barBg}`} />

        {/* Card Content Padding */}
        <div className="p-4 space-y-3">
          {/* Header Row: Category Icon + Authority Name & Sub-tag + MANDATORY/OPTIONAL Badge */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center space-x-2.5 min-w-0 flex-1">
              <div className={`p-2 rounded-xl ${theme.iconBg} flex items-center justify-center shrink-0`}>
                <CategoryIcon className="w-4 h-4 stroke-[2]" />
              </div>
              <div className="min-w-0 flex-1">
                <span 
                  className="text-[11px] font-bold text-slate-800 tracking-wider uppercase block truncate"
                  title={data.authority || "Government Authority"}
                >
                  {data.authority || "Government Authority"}
                </span>
                <span className="text-[10px] text-slate-500 font-medium block truncate">
                  {data.category ? `${data.category.toUpperCase()} PERMISSION` : 'STATUTORY PERMISSION'}
                </span>
              </div>
            </div>

            {/* MANDATORY / OPTIONAL Pill */}
            <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border shrink-0 ${
              data.mandatory 
                ? 'bg-rose-50 text-rose-700 border-rose-200' 
                : 'bg-slate-50 text-slate-600 border-slate-200'
            }`}>
              {data.mandatory ? 'MANDATORY' : 'OPTIONAL'}
            </span>
          </div>

          {/* Main Approval Title */}
          <div>
            <h4 className="font-extrabold text-slate-900 text-sm leading-snug line-clamp-2 hover:text-emerald-700 transition-colors">
              {data.label}
            </h4>
            <p className="text-[11px] text-slate-500 font-medium truncate mt-0.5">
              {data.department || "Government of Maharashtra"}
            </p>
          </div>

          {/* Bottom Row Badges: Duration & Official Portal Indicator */}
          <div className="flex items-center justify-between pt-2.5 border-t border-slate-100 text-[11px]">
            <div className="flex items-center space-x-1.5 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200/80 font-semibold text-slate-600">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <span>~{data.estimated_duration_days || 30} Days</span>
            </div>

            <div className="flex items-center space-x-1 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200/80 font-semibold text-slate-500 text-[10px]">
              <AlertCircle className="w-3.5 h-3.5 text-slate-400" />
              <span>Official Portal</span>
            </div>
          </div>
        </div>
      </div>

      {/* Source Connection Handle */}
      <Handle
        type="source"
        position={sourcePosition}
        id="source"
      />
    </div>
  );
}

export default memo(ApprovalNode);
