const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';

export function connectToStream(queryId, handlers) {
  const url = `${BASE_URL}/queries/${queryId}/stream`;
  const eventSource = new EventSource(url);
  let isClosed = false;

  eventSource.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data);
      const data = parsed.data || parsed;
      if (handlers.onStep && (parsed.event === 'step' || data.event_type === 'step')) {
        handlers.onStep(data);
      } else if (handlers.onComplete && (parsed.event === 'complete' || data.event_type === 'complete')) {
        isClosed = true;
        handlers.onComplete(data);
        eventSource.close();
      }
    } catch (err) {
      console.error('Failed to parse SSE event:', err);
    }
  };

  eventSource.addEventListener('step', (event) => {
    try {
      const parsed = JSON.parse(event.data);
      const data = parsed.data || parsed;
      if (handlers.onStep) handlers.onStep(data);
    } catch (e) {
      console.error(e);
    }
  });

  eventSource.addEventListener('decision', (event) => {
    try {
      const parsed = JSON.parse(event.data);
      const data = parsed.data || parsed;
      if (handlers.onDecision) handlers.onDecision(data);
    } catch (e) {
      console.error(e);
    }
  });

  eventSource.addEventListener('complete', (event) => {
    try {
      isClosed = true;
      const parsed = JSON.parse(event.data);
      const data = parsed.data || parsed;
      if (handlers.onComplete) handlers.onComplete(data);
      eventSource.close();
    } catch (e) {
      console.error(e);
    }
  });

  const phase3Events = [
    'claim:extracted', 'claim:verified', 'claim:disputed',
    'contradiction:detected', 'contradiction:resolved',
    'source:scored', 'evidence:graph_updated'
  ];

  phase3Events.forEach(eventType => {
    eventSource.addEventListener(eventType, (event) => {
      try {
        const parsed = JSON.parse(event.data);
        const data = parsed.data || parsed;
        if (handlers.onPhase3Event) handlers.onPhase3Event(eventType, data);
      } catch (e) {
        console.error(e);
      }
    });
  });

  eventSource.onerror = (err) => {
    if (isClosed || eventSource.readyState === EventSource.CLOSED || eventSource.readyState === EventSource.CONNECTING) {
      return;
    }
    isClosed = true;
    eventSource.close();
    if (handlers.onError) {
      handlers.onError(err);
    }
  };

  return () => {
    isClosed = true;
    eventSource.close();
  };
}
