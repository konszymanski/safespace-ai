import { useState } from "react";
import DisclaimerGate from "@/components/DisclaimerGate";
import QuickExitBar from "@/components/QuickExitBar";
import ChatView from "@/components/ChatView";

const Index = () => {
  const [accepted, setAccepted] = useState(false);
  const [shreddingTick, setShreddingTick] = useState(0);

  return (
    <div className="min-h-screen flex flex-col bg-gradient-calm">
      <DisclaimerGate onAccept={() => setAccepted(true)} />

      {accepted && (
        <>
          <QuickExitBar onShred={() => setShreddingTick((t) => t + 1)} />
          <ChatView shreddingTick={shreddingTick} />
        </>
      )}
    </div>
  );
};

export default Index;
