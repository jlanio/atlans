"use client"
import '@xyflow/react/dist/style.css';
import ReactFlowComponent from '@/app/components/workflow';
import { ReactFlowProvider } from '@xyflow/react';
import { FlowContextProvider } from '@/context/useFlowContext';

export default function WorkFlowCreatePage() {

  return (
    <div className='w-full h-full'>

      <ReactFlowProvider>
        <FlowContextProvider>
          <ReactFlowComponent />
        </FlowContextProvider>
      </ReactFlowProvider>

    </div>
  );
}