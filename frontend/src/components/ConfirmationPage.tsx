import React from 'react';
import { CheckCircle2, Mail, FileText, Calendar, User, ArrowLeft } from 'lucide-react';
import { useEffect } from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import { PortalLogos } from './PortalLogos';

interface ConfirmationPageProps {
  email: string;
  uploaderName: string;
  projectTitle: string;
  uploadedFiles: Array<{ categoryKey: string; fileName: string }>;
  uploadTimestamp: string;
  onNewUpload: () => void;
}

export function ConfirmationPage({
  email,
  uploaderName,
  projectTitle,
  uploadedFiles,
  uploadTimestamp,
  onNewUpload,
}: ConfirmationPageProps) {
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const { t, language } = useLanguage();

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    const locale = language === 'de' ? 'de-DE' : 'en-US';
    return date.toLocaleString(locale, {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-white to-blue-50 py-8 px-4">
      <div className="max-w-3xl mx-auto">
        {/* Top Bar */}
        <div className="flex items-center justify-start mb-6">
          <PortalLogos />
        </div>

        {/* Success Header */}
        <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-8 mb-6 text-center">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="w-12 h-12 text-green-600" />
          </div>
          
          <h1 className="text-gray-900 mb-2">{t('confirmation.success')}</h1>
          
          <p className="text-gray-600 max-w-xl mx-auto">
            {t('confirmation.message')}
          </p>
        </div>

        {/* Upload Details */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-gray-900 mb-4">{t('confirmation.details')}</h2>
          
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <FileText className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-gray-500 text-sm">{t('confirmation.projectTitle')}</p>
                <p className="text-gray-900">{projectTitle}</p>
              </div>
            </div>

            {uploaderName && (
              <div className="flex items-start gap-3">
                <User className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-gray-500 text-sm">{t('confirmation.uploader')}</p>
                  <p className="text-gray-900">{uploaderName}</p>
                </div>
              </div>
            )}

            <div className="flex items-start gap-3">
              <Mail className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-gray-500 text-sm">{t('confirmation.email')}</p>
                <p className="text-gray-900 break-all">{email}</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Calendar className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-gray-500 text-sm">{t('confirmation.timestamp')}</p>
                <p className="text-gray-900">{formatDate(uploadTimestamp)}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Uploaded Files */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-gray-900 mb-4">
            {t('confirmation.documents')} ({uploadedFiles.length})
          </h2>
          
          <div className="space-y-2">
            {uploadedFiles.map((file, index) => (
              <div
                key={index}
                className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200"
              >
                <FileText className="w-5 h-5 text-blue-600 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-gray-900 truncate">{file.fileName}</p>
                  <p className="text-gray-500 text-sm">{t(`category.${file.categoryKey}`)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* E-Mail Notification */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
          <div className="flex gap-3">
            <Mail className="w-6 h-6 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-blue-900 mb-2">{t('confirmation.emailNotification')}</h3>
              <p className="text-blue-800 mb-3">
                {t('confirmation.emailSent', { email })}
              </p>

            </div>
          </div>
        </div>

        {/* Next Steps */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h3 className="text-gray-900 mb-3">{t('confirmation.nextSteps')}</h3>
          <ul className="space-y-2 text-gray-700">
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-1">•</span>
              <span>{t('confirmation.keepEmailProof')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-1">•</span>
              <span>{t('confirmation.step1')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-1">•</span>
              <span>{t('confirmation.step2')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-1">•</span>
              <span>{t('confirmation.step3')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-1">•</span>
              <span>{t('confirmation.step4')}</span>
            </li>
          </ul>
          <p className="mt-3 text-gray-700">{t('confirmation.note')}</p>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4">
          <button
            onClick={onNewUpload}
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-3 px-6 rounded-lg flex items-center justify-center gap-2 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>{t('confirmation.newUpload')}</span>
          </button>
        </div>

        {/* Footer Info */}
        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>{t('confirmation.footer')}</p>
          <p>{t('confirmation.emailContact')}</p>
        </div>
      </div>
    </div>
  );
}
