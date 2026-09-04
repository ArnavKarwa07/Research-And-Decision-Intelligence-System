import React, { useState } from 'react';

export default function ClarificationPromptCard({ clarification, onAnswer }) {
  const [customAnswer, setCustomAnswer] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!clarification) return null;

  const handleSubmit = async (answerText) => {
    setIsSubmitting(true);
    try {
      if (onAnswer) {
        await onAnswer(clarification.id, answerText);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const isPending = clarification.status === 'pending';

  return (
    <div style={{
      border: '1px solid #9c27b0',
      borderRadius: '8px',
      padding: '16px',
      backgroundColor: '#fef5ff',
      marginBottom: '16px'
    }}>
      <h4 style={{ margin: '0 0 8px 0', color: '#7b1fa2', fontSize: '1.05rem' }}>
        ❓ Clarification Required
      </h4>
      <p style={{ margin: '0 0 12px 0', fontSize: '0.9rem', color: '#333' }}>
        {clarification.prompt}
      </p>

      {isPending ? (
        <div>
          {clarification.options && clarification.options.length > 0 && (
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '10px' }}>
              {clarification.options.map((opt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSubmit(opt)}
                  disabled={isSubmitting}
                  style={{
                    backgroundColor: '#f3e5f5',
                    color: '#7b1fa2',
                    border: '1px solid #ab47bc',
                    padding: '6px 12px',
                    borderRadius: '16px',
                    cursor: 'pointer',
                    fontSize: '0.85rem'
                  }}
                >
                  {opt}
                </button>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              type="text"
              placeholder="Or type custom clarification instructions..."
              value={customAnswer}
              onChange={(e) => setCustomAnswer(e.target.value)}
              style={{
                flex: 1,
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #ccc',
                fontSize: '0.85rem'
              }}
            />
            <button
              onClick={() => handleSubmit(customAnswer)}
              disabled={isSubmitting || !customAnswer.trim()}
              style={{
                backgroundColor: '#7b1fa2',
                color: 'white',
                border: 'none',
                padding: '6px 16px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: 500
              }}
            >
              Submit Answer
            </button>
          </div>
        </div>
      ) : (
        <div style={{ fontSize: '0.85rem', color: '#4a148c', fontWeight: 600 }}>
          Answered: {clarification.answer}
        </div>
      )}
    </div>
  );
}
