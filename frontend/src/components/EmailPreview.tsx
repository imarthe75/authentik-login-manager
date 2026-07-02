import React from 'react';
import { Theme } from '../types/theme';

interface EmailPreviewProps {
  theme: Theme;
  eventType: string;
}

export const EmailPreview: React.FC<EmailPreviewProps> = ({ theme, eventType }) => {
  const emailBody = theme.email_bodies?.[eventType as any];

  if (!emailBody || !emailBody.body_html) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-100">
        <div className="text-center text-gray-500">
          <p className="text-lg font-semibold mb-2">📧 Sin contenido</p>
          <p className="text-sm">Edita el contenido en el panel derecho para ver el preview</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full overflow-auto bg-gray-100 p-4">
      <div className="bg-white rounded-lg shadow-sm" style={{ maxWidth: '600px', margin: '0 auto' }}>
        <iframe
          srcDoc={emailBody.body_html}
          className="w-full border-none rounded-lg"
          style={{ height: 'calc(100vh - 200px)', minHeight: '400px' }}
          title="Email preview"
        />
      </div>
    </div>
  );
};
