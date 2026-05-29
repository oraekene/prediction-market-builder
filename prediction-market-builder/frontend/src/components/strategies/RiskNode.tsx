import { Handle, Position } from '@xyflow/react';

export default function RiskNode({ data }: { data: any }) {
  return (
    <div className="bg-gray-950 border border-red-800/50 rounded-lg px-4 py-3 min-w-[180px] shadow-lg">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-red-950/50 text-red-400 border border-red-800/30">
          Risk
        </span>
        {data.triggered && (
          <span className="text-[9px] font-medium px-1 py-0.5 rounded bg-red-500/20 text-red-300 border border-red-500/30">
            Triggered
          </span>
        )}
      </div>
      <p className="text-sm font-medium text-gray-100 leading-tight">{data.label}</p>
      {data.backendType && (
        <p className="text-[10px] text-gray-500 mt-1 font-mono">{data.backendType}</p>
      )}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-2.5 !h-2.5 !bg-red-500 !border-2 !border-gray-950"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!w-2.5 !h-2.5 !bg-red-500 !border-2 !border-gray-950"
      />
    </div>
  );
}
