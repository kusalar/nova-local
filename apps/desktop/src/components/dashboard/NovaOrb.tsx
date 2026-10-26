import React from 'react';
import { motion } from 'framer-motion';
import { NovaState } from '../../types';

interface NovaOrbProps {
  state: NovaState;
  statusMessage?: string;
  onClick?: () => void;
  partialTranscript?: string;
  lastTranscript?: string;
  audioLevel?: number;
}

export const NovaOrb: React.FC<NovaOrbProps> = ({
  state = 'IDLE',
  statusMessage = 'NOVA SYSTEM ONLINE',
  onClick,
  partialTranscript,
  lastTranscript,
  audioLevel = 0
}) => {
  // Color configuration depending on state
  const stateConfig = {
    IDLE: {
      primary: '#00f0ff',
      secondary: '#0077ff',
      glow: 'rgba(0, 240, 255, 0.45)',
      pulseSpeed: 3.5,
      rotationSpeed: 30,
    },
    LISTENING: {
      primary: '#00ffd5',
      secondary: '#00b4cc',
      glow: 'rgba(0, 255, 213, 0.7)',
      pulseSpeed: 1.2,
      rotationSpeed: 15,
    },
    THINKING: {
      primary: '#9d4edd',
      secondary: '#00f0ff',
      glow: 'rgba(157, 78, 221, 0.65)',
      pulseSpeed: 0.8,
      rotationSpeed: 8,
    },
    EXECUTING: {
      primary: '#0077ff',
      secondary: '#00ffd5',
      glow: 'rgba(0, 119, 255, 0.6)',
      pulseSpeed: 1.5,
      rotationSpeed: 12,
    },
    SPEAKING: {
      primary: '#00f0ff',
      secondary: '#38bdf8',
      glow: 'rgba(0, 240, 255, 0.8)',
      pulseSpeed: 1.0,
      rotationSpeed: 16,
    },
    ERROR: {
      primary: '#ff3366',
      secondary: '#f59e0b',
      glow: 'rgba(255, 51, 102, 0.75)',
      pulseSpeed: 0.6,
      rotationSpeed: 40,
    }
  };

  const current = stateConfig[state] || stateConfig.IDLE;

  return (
    <div 
      onClick={onClick}
      className="relative flex flex-col items-center justify-center p-6 cursor-pointer select-none group"
      title="Click to interact with NOVA"
    >
      {/* Outer ambient glow */}
      <div 
        className="absolute w-80 h-80 rounded-full blur-3xl opacity-30 transition-all duration-700 pointer-events-none"
        style={{
          background: `radial-gradient(circle, ${current.glow} 0%, transparent 70%)`
        }}
      />

      {/* Main 3D Spherical AI Core Container */}
      <div className="relative w-64 h-64 flex items-center justify-center">
        {/* Outer Orbital Ring 1 (Tilted 30deg) */}
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: current.rotationSpeed, repeat: Infinity, ease: 'linear' }}
          className="absolute w-60 h-60 rounded-full border border-dashed transition-colors duration-500 pointer-events-none"
          style={{
            borderColor: current.primary,
            opacity: 0.45,
            transform: 'rotateX(65deg) rotateY(20deg)'
          }}
        />

        {/* Outer Orbital Ring 2 (Tilted -35deg) */}
        <motion.div
          animate={{ rotate: -360 }}
          transition={{ duration: current.rotationSpeed * 1.3, repeat: Infinity, ease: 'linear' }}
          className="absolute w-64 h-64 rounded-full border transition-colors duration-500 pointer-events-none"
          style={{
            borderColor: current.secondary,
            opacity: 0.35,
            borderWidth: '1.5px',
            transform: 'rotateX(55deg) rotateY(-30deg)'
          }}
        >
          {/* Orbital satellite node */}
          <div 
            className="w-2.5 h-2.5 rounded-full absolute -top-1 left-1/2 shadow-lg"
            style={{ backgroundColor: current.primary, boxShadow: `0 0 10px ${current.primary}` }}
          />
        </motion.div>

        {/* Outer Wireframe Latitude Rings */}
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: current.rotationSpeed * 1.8, repeat: Infinity, ease: 'linear' }}
          className="absolute w-52 h-52 rounded-full border transition-colors duration-500 pointer-events-none"
          style={{
            borderColor: current.primary,
            opacity: 0.25,
            borderStyle: 'dashed'
          }}
        />

        {/* Inner Spherical Wireframe Cage (SVG) */}
        <svg className="absolute w-48 h-48 pointer-events-none" viewBox="0 0 200 200">
          <defs>
            <radialGradient id="orbCoreGradient" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="0.9" />
              <stop offset="35%" stopColor={current.primary} stopOpacity="0.75" />
              <stop offset="70%" stopColor={current.secondary} stopOpacity="0.4" />
              <stop offset="100%" stopColor="transparent" stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* Spherical Longitude Ellipses */}
          <ellipse cx="100" cy="100" rx="90" ry="90" fill="none" stroke={current.primary} strokeWidth="1" opacity="0.3" />
          <ellipse cx="100" cy="100" rx="65" ry="90" fill="none" stroke={current.primary} strokeWidth="0.8" opacity="0.4" />
          <ellipse cx="100" cy="100" rx="35" ry="90" fill="none" stroke={current.primary} strokeWidth="0.8" opacity="0.35" />
          
          {/* Spherical Latitude Ellipses */}
          <ellipse cx="100" cy="100" rx="90" ry="60" fill="none" stroke={current.primary} strokeWidth="0.8" opacity="0.4" />
          <ellipse cx="100" cy="100" rx="90" ry="30" fill="none" stroke={current.primary} strokeWidth="0.8" opacity="0.45" />

          {/* Central Radial Glowing Core */}
          <circle cx="100" cy="100" r="45" fill="url(#orbCoreGradient)" />
        </svg>

        {/* Central Core Breathing Orb */}
        <motion.div
          animate={{
            scale: state === 'THINKING' ? [1, 1.25, 0.95, 1.2, 1] : [0.95, 1.08, 0.95],
            opacity: state === 'ERROR' ? [0.6, 1, 0.6] : [0.85, 1, 0.85]
          }}
          transition={{
            duration: current.pulseSpeed,
            repeat: Infinity,
            ease: 'easeInOut'
          }}
          className="relative z-10 flex flex-col items-center justify-center w-36 h-36 rounded-full"
          style={{
            boxShadow: `0 0 35px ${current.glow}, inset 0 0 20px rgba(255, 255, 255, 0.3)`
          }}
        >
          {/* Futuristic Branding in Center */}
          <h1 className="font-display font-black text-2xl tracking-[0.25em] text-white drop-shadow-[0_0_12px_rgba(255,255,255,0.8)]">
            NOVA
          </h1>
          <span className="font-display font-semibold text-[10px] tracking-[0.3em] text-cyan-200 uppercase mt-[-2px]">
            AI CORE
          </span>
          <span className="font-mono text-[9px] text-cyan-300/80 tracking-widest mt-1">
            v0.1.0
          </span>
        </motion.div>
      </div>

      {/* Ground Holographic Grid Rings (Perspective Projection) */}
      <div className="relative w-72 h-16 mt-[-18px] flex items-center justify-center pointer-events-none">
        <div 
          className="w-64 h-16 rounded-full border border-nova-cyan/20 holo-ground"
          style={{
            boxShadow: '0 0 15px rgba(0, 240, 255, 0.15)',
            backgroundImage: 'radial-gradient(ellipse at center, rgba(0, 240, 255, 0.12) 0%, transparent 70%)'
          }}
        />
        <div className="absolute w-44 h-10 rounded-full border border-dashed border-nova-cyan/30 holo-ground" />
      </div>

      {/* Assistant Status Label */}
      <div className="mt-2 flex flex-col items-center max-w-md w-full">
        <div className="flex items-center gap-2 px-3.5 py-1 rounded-full bg-nova-dark/90 border border-nova-border shadow-md">
          <span 
            className="w-2 h-2 rounded-full animate-ping"
            style={{ backgroundColor: current.primary }}
          />
          <span className="font-display font-bold text-xs tracking-widest text-slate-200 uppercase truncate max-w-[280px]">
            {statusMessage}
          </span>
        </div>

        {/* Real-time live transcript display */}
        {partialTranscript && (
          <div className="mt-2 px-3 py-1 rounded bg-teal-950/70 border border-teal-500/50 text-teal-300 font-mono text-xs animate-pulse max-w-full text-center truncate">
            <span className="text-[10px] text-teal-400 font-bold mr-1">HEARING:</span>
            "{partialTranscript}"
          </div>
        )}

        {!partialTranscript && lastTranscript && state !== 'LISTENING' && (
          <div className="mt-1.5 px-3 py-0.5 rounded bg-nova-surface/80 border border-nova-cyan/30 text-nova-cyan font-mono text-[11px] max-w-full text-center truncate">
            <span className="text-[10px] text-nova-textDim mr-1">TRANSCRIPT:</span>
            "{lastTranscript}"
          </div>
        )}

        <span className="text-[10px] text-slate-400 font-mono tracking-wider mt-1 opacity-75">
          STATE: <span className="font-semibold text-nova-cyan">{state}</span> • {state === 'LISTENING' ? 'CLICK TO FINALIZE' : 'CLICK TO SPEAK'}
        </span>
      </div>
    </div>
  );
};
