import { FileCategory } from '../types';
import { generateRequestId, log } from '../utils/logger';

export interface UploadData {
  email: string;
  uploaderName: string;
  projectTitle: string;
  institution: string;
  isProspectiveStudy: boolean;
  projectDetails?: string;
  categories: FileCategory[];
  projectType: 'new' | 'existing' | null;
  language: 'de' | 'en';
}

export interface UploadResult {
  success: boolean;
  timestamp: string;
  project_id?: string;
  files_uploaded?: number;
  message?: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
// VITE_API_TOKEN is the static server-to-server secret.
// It is only used to obtain a short-lived upload token from /api/upload-token
// and is never sent directly to the upload endpoint.
const API_TOKEN = import.meta.env.VITE_API_TOKEN;

export class ApiError extends Error {
  public readonly i18nKey: string;

  constructor(i18nKey: string) {
    super(i18nKey);
    this.name = 'ApiError';
    this.i18nKey = i18nKey;
  }
}

/**
 * Exchange the static API token for a short-lived upload JWT.
 * This limits the exposure of the static secret: it is only used once per upload
 * session, and the resulting JWT expires after a few minutes (OWASP A07).
 */
async function fetchUploadToken(): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/upload-token`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${API_TOKEN}`,
    },
  });
  if (!response.ok) {
    throw new ApiError('error.authFailed');
  }
  const data = await response.json();
  return data.token as string;
}

export const api = {
  upload: async (data: UploadData): Promise<UploadResult> => {
    const requestId = generateRequestId();
    log.info('api_upload_start', {
      requestId,
      projectType: data.projectType,
      categoriesCount: data.categories.length,
      totalFiles: data.categories.reduce((sum, cat) => sum + cat.files.length, 0),
    });

    // Basic validation before even trying
    if (!API_TOKEN) {
      log.error('api_config_missing_token');
      throw new ApiError('error.configMissingToken');
    }

    if (!API_BASE_URL) {
      log.error('api_config_missing_base_url');
      throw new ApiError('error.configMissingApiUrl');
    }

    // Obtain a short-lived upload token (OWASP A07 – token not embedded in upload)
    let uploadToken: string;
    try {
      uploadToken = await fetchUploadToken();
      log.debug('api_upload_token_obtained', { requestId });
    } catch {
      log.error('api_upload_token_fetch_failed', { requestId });
      throw new ApiError('error.authFailed');
    }

    const formData = new FormData();

    // Add basic fields
    formData.append('email', data.email);
    if (data.uploaderName) {
      formData.append('uploader_name', data.uploaderName);
    }
    formData.append('project_title', data.projectTitle);
    formData.append('institution', data.institution);
    formData.append('is_prospective_study', String(data.isProspectiveStudy));
    if (data.projectDetails) {
      formData.append('project_details', data.projectDetails);
    }
    formData.append('project_type', data.projectType || 'new');
    formData.append('language', data.language);

    // Process files and categories
    const categoryMap: Record<string, string> = {};
    let totalFileSize = 0;

    data.categories.forEach((category) => {
      category.files.forEach((file) => {
        let fileToUpload = file;

        // Renaming logic based on requirements
        let prefix = '';
        // Use first 10 chars of title, replace potentially problematic chars for filenames
        const titlePart = data.projectTitle.substring(0, 10).replace(/[\/\\:]/g, '_');

        switch (category.key) {
          case 'verantwortung':
            prefix = 'Verpflichtung_';
            break;
          case 'schulung_uni':
            prefix = 'SchulungGU_';
            break;
          case 'schulung_ukf':
            prefix = 'SchulungUKF_';
            break;
          case 'datenschutzkonzept':
            prefix = `DSK_${titlePart}_`;
            break;
          case 'einwilligung':
            prefix = `EW_${titlePart}_`;
            break;
          case 'ethikvotum':
            prefix = 'ethik_';
            break;
          // 'sonstiges' keeps original name as per implied requirements (only specific prefixes listed)
        }

        if (prefix) {
          const newName = prefix + file.name;
          fileToUpload = new File([file], newName, { type: file.type });
          log.debug('api_file_renamed');
        }

        formData.append('files', fileToUpload);
        categoryMap[fileToUpload.name] = category.key;
        totalFileSize += fileToUpload.size;
        log.debug('api_file_added_to_formdata', { fileSize: fileToUpload.size, category: category.key });
      });
    });

    // Add category mapping
    formData.append('file_categories', JSON.stringify(categoryMap));
    log.debug('api_upload_payload_prepared', {
      requestId,
      totalUploadSizeMb: Number((totalFileSize / 1024 / 1024).toFixed(2)),
    });

    const uploadUrl = `${API_BASE_URL}/upload`;
    log.debug('api_request_sending', { requestId });

    try {
      const startTime = Date.now();
      const response = await fetch(uploadUrl, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${uploadToken}`,
          'X-Request-ID': requestId,
        },
        body: formData,
      });

      const duration = Date.now() - startTime;
      log.info('api_response_received', {
        requestId,
        durationMs: duration,
        status: response.status,
        statusText: response.statusText,
      });

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          log.error('api_auth_failed', {
            requestId,
            status: response.status,
            statusText: response.statusText
          });
          throw new ApiError('error.authFailed');
        } else {
          try {
            await response.json();
            log.error('api_upload_failed_with_json_error', { requestId, status: response.status });
          } catch (parseError) {
            await response.text().catch(() => 'Unable to read error response');
            log.error('api_upload_failed_unparseable_error', {
              requestId,
              status: response.status,
              statusText: response.statusText,
            });
          }
          throw new ApiError('error.uploadFailed');
        }
      }

      const result = await response.json();
      log.info('api_upload_success', { requestId });

      return {
        success: result.success,
        timestamp: result.timestamp,
        project_id: result.project_id,
        files_uploaded: result.files_uploaded,
        message: result.message,
      };
    } catch (error) {
      if (error instanceof Error) {
        log.error('api_upload_error', {
          requestId,
          message: error.message,
          name: error.name,
          stack: error.stack
        });
      } else {
        log.error('api_upload_error_unknown', { requestId });
      }
      // Re-throw with user-friendly message if possible, or pass through
      throw error;
    }
  }
};
