const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

const formatMsg = (val) => (typeof val === 'object' && val !== null ? JSON.stringify(val) : String(val));

const parseErrorData = (event) => {
  if (!event) return { message: 'Stream connection interrupted.' };
  if (typeof event === 'string') return { message: event };
  if (event.message) return { message: formatMsg(event.message) };
  if (event.data) {
    try {
      const parsed = JSON.parse(event.data);
      const msg = parsed.message || parsed.detail || event.data;
      return { message: formatMsg(msg) };
    } catch (e) {
      return { message: formatMsg(event.data) };
    }
  }
  return { message: 'Stream connection interrupted.' };
};

export function connectToStream(queryId, handlers) {
  const url = `${BASE_URL}/queries/${queryId}/stream`;
  const eventSource = new EventSource(url);
  let isClosed = false;

  eventSource.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data);
      const data = parsed.data || parsed;
      const eventType = parsed.event_type || parsed.event || data.event_type;
      if (eventType === 'error' && handlers.onError) {
        isClosed = true;
        try {
          handlers.onError(parseErrorData(event));
        } finally {
          eventSource.close();
        }
      } else if (handlers.onStep && eventType === 'step') {
        handlers.onStep(data);
      } else if (handlers.onEvidence && eventType === 'evidence') {
        handlers.onEvidence(data);
      } else if (handlers.onClaim && eventType === 'claim') {
        handlers.onClaim(data);
      } else if (handlers.onDecision && eventType === 'decision') {
        handlers.onDecision(data);
      } else if (handlers.onComplete && eventType === 'complete') {
        isClosed = true;
        try {
          handlers.onComplete(data);
        } finally {
          eventSource.close();
        }
      }
    } catch (err) {
      console.error('Failed to parse SSE event:', err);
    }
  };

  eventSource.addEventListener('evidence', (event) => {
    try {
      const parsed = JSON.parse(event.data);
      const data = parsed.data || parsed;
      if (handlers.onEvidence) handlers.onEvidence(data);
    } catch (e) {
      console.error(e);
    }
  });

  eventSource.addEventListener('claim', (event) => {
    try {
      const parsed = JSON.parse(event.data);
      const data = parsed.data || parsed;
      if (handlers.onClaim) handlers.onClaim(data);
    } catch (e) {
      console.error(e);
    }
  });

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
    isClosed = true;
    try {
      const parsed = JSON.parse(event.data);
      const data = parsed.data || parsed;
      if (handlers.onComplete) handlers.onComplete(data);
    } catch (e) {
      console.error(e);
    } finally {
      eventSource.close();
    }
  });

  eventSource.addEventListener('error', (event) => {
    if (isClosed) return;
    isClosed = true;
    try {
      if (handlers.onError) {
        handlers.onError(parseErrorData(event));
      }
    } finally {
      eventSource.close();
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
    if (isClosed) return;
    isClosed = true;
    try {
      if (handlers.onError) {
        handlers.onError(parseErrorData(err));
      }
    } finally {
      eventSource.close();
    }
  };

  return () => {
    isClosed = true;
    eventSource.close();
  };
}
