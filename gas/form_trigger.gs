/**
 * 経費精算マルチエージェントシステム - Google Apps Script
 *
 * Google Formの送信をトリガーにして、Cloud Run上の
 * 経費精算チェックAPIを呼び出し、結果をスプレッドシートに記録する。
 *
 * セットアップ手順:
 * 1. フォームにリンクされたスプレッドシートを開く
 * 2. 拡張機能 > Apps Script でこのスクリプトを貼り付け
 * 3. スクリプトプロパティに API_URL を設定
 * 4. setupTrigger() を1回実行
 */

// =============================================================
// 設定
// =============================================================

/**
 * スクリプトプロパティから設定値を取得。
 *
 * プロジェクトの設定 > スクリプトプロパティ:
 *   API_URL: Cloud RunのURL
 *            例: https://expense-agent-xxxxx-an.a.run.app
 */
function getConfig_() {
  const props = PropertiesService.getScriptProperties();
  return {
    apiUrl: props.getProperty('API_URL') || '',
  };
}

/**
 * フォームの質問タイトルとAPIフィールドの対応。
 * フォームの質問タイトルに合わせて設定。
 */
const FORM_FIELDS = {
  email: 'メールアドレス',
  date: '利用日',
  type: '申請種別',
  applicant: '申請者（氏名・所属部署）',
  amount: '合計金額',
  count: '参加者数（合計）',
  participantsInternal: '参加者の所属・氏名一覧',
  participantsExternal: '先方の会社名・氏名・役職',
  purpose: '目的・備考',
  receipt: '領収書のアップロード',
};

// 審査結果を書き込む列ヘッダー
const RESULT_HEADERS = [
  '審査ステータス',
  '確信度スコア',
  '審査詳細',
  '却下理由',
  '審査日時',
];

// =============================================================
// メイン処理
// =============================================================

/**
 * フォーム送信時に自動実行されるトリガー関数。
 *
 * @param {Object} e - フォーム送信イベントオブジェクト
 */
function onFormSubmit(e) {
  try {
    const formData = extractFormData_(e);
    const result = callExpenseCheckApi_(formData);
    writeResultToSheet_(e, result);
    sendNotificationEmail_(formData, result);
  } catch (error) {
    Logger.log('Error in onFormSubmit: ' + error.message);
    Logger.log(error.stack);
  }
}

// =============================================================
// データ抽出
// =============================================================

/**
 * フォーム送信イベントからAPIリクエスト用データを抽出。
 *
 * 申請種別に応じて参加者情報の取得元を切り替える:
 * - 社内懇親会 → 「参加者の所属・氏名一覧」
 * - 社外接待   → 「先方の会社名・氏名・役職」
 *
 * @param {Object} e - フォーム送信イベント
 * @returns {Object} APIリクエスト用データ
 */
function extractFormData_(e) {
  const nv = e.namedValues;

  const type = getNamedValue_(nv, FORM_FIELDS.type);
  const amount = parseInt(
    getNamedValue_(nv, FORM_FIELDS.amount), 10
  ) || 0;
  const count = parseInt(
    getNamedValue_(nv, FORM_FIELDS.count), 10
  ) || 0;

  // 申請種別に応じて参加者情報を取得
  let participantsRaw = '';
  if (type.indexOf('社外接待') !== -1) {
    participantsRaw =
      getNamedValue_(nv, FORM_FIELDS.participantsExternal);
  } else {
    participantsRaw =
      getNamedValue_(nv, FORM_FIELDS.participantsInternal);
  }

  // 領収書URL（ファイルアップロードはDrive URLとして記録される）
  const receiptUrl =
    getNamedValue_(nv, FORM_FIELDS.receipt) || null;

  // 目的（申請者情報も付加して判断材料を増やす）
  const applicant = getNamedValue_(nv, FORM_FIELDS.applicant);
  const purpose = getNamedValue_(nv, FORM_FIELDS.purpose);
  const date = getNamedValue_(nv, FORM_FIELDS.date);
  const purposeFull =
    purpose + '（申請者: ' + applicant + ', 利用日: ' + date + '）';

  return {
    type: type,
    amount: amount,
    count: count,
    participants_raw: participantsRaw,
    purpose: purposeFull,
    receipt_url: receiptUrl,
  };
}

/**
 * namedValuesから安全に値を取得するヘルパー。
 *
 * @param {Object} namedValues - e.namedValues
 * @param {string} fieldName - フィールド名
 * @returns {string} 値（なければ空文字列）
 */
function getNamedValue_(namedValues, fieldName) {
  const values = namedValues[fieldName];
  if (values && values.length > 0) {
    return values[0].trim();
  }
  return '';
}

// =============================================================
// API呼び出し
// =============================================================

/**
 * Cloud Run上の経費精算チェックAPIを呼び出す。
 *
 * @param {Object} formData - APIリクエストデータ
 * @returns {Object} API応答（パース済み）
 */
function callExpenseCheckApi_(formData) {
  const config = getConfig_();

  if (!config.apiUrl) {
    throw new Error(
      'API_URL が設定されていません。'
      + 'スクリプトプロパティに設定してください。'
    );
  }

  const url = config.apiUrl + '/api/expense-check';

  const options = {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(formData),
    muteHttpExceptions: true,
    headers: getAuthHeaders_(),
  };

  Logger.log('API Request: ' + JSON.stringify(formData));

  const response = UrlFetchApp.fetch(url, options);
  const statusCode = response.getResponseCode();

  if (statusCode !== 200) {
    Logger.log(
      'API Error: ' + statusCode + ' - '
      + response.getContentText()
    );
    return {
      status: '要人間確認',
      confidence_score: 0,
      details: {error: 'API呼び出しエラー: ' + statusCode},
      rejection_reason: null,
    };
  }

  const result = JSON.parse(response.getContentText());
  Logger.log('API Response: ' + JSON.stringify(result));
  return result;
}

/**
 * Cloud Run認証用ヘッダーを取得。
 *
 * --allow-unauthenticated の場合は空。
 * 認証必須の場合はIDトークンを自動付与。
 */
function getAuthHeaders_() {
  try {
    const token = ScriptApp.getIdentityToken();
    if (token) {
      return {'Authorization': 'Bearer ' + token};
    }
  } catch (e) {
    // 認証不要の場合はスキップ
  }
  return {};
}

// =============================================================
// 結果書き込み
// =============================================================

/**
 * 審査結果をスプレッドシートの回答行に追記。
 *
 * @param {Object} e - フォーム送信イベント
 * @param {Object} result - API応答
 */
function writeResultToSheet_(e, result) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet()
    .getActiveSheet();
  const lastRow = sheet.getLastRow();

  // 結果列のヘッダーが未設定なら追加
  ensureResultHeaders_(sheet);

  // 結果列の開始位置を特定
  const headers = sheet.getRange(
    1, 1, 1, sheet.getLastColumn()
  ).getValues()[0];
  let resultColStart = headers.indexOf(RESULT_HEADERS[0]) + 1;

  if (resultColStart === 0) {
    resultColStart = headers.length + 1;
  }

  // 詳細を読みやすく整形
  let detailsText = '';
  if (result.details) {
    const details = result.details;
    const lines = Object.keys(details).map(function(key) {
      return key + ': ' + details[key];
    });
    detailsText = lines.join('\n');
  }

  const resultRow = [
    result.status || '不明',
    result.confidence_score || 0,
    detailsText,
    result.rejection_reason || '',
    new Date().toLocaleString('ja-JP'),
  ];

  sheet.getRange(lastRow, resultColStart, 1, resultRow.length)
    .setValues([resultRow]);
}

/**
 * スプレッドシートに結果列ヘッダーが無ければ追加。
 */
function ensureResultHeaders_(sheet) {
  const headers = sheet.getRange(
    1, 1, 1, sheet.getLastColumn()
  ).getValues()[0];

  if (headers.indexOf(RESULT_HEADERS[0]) === -1) {
    const startCol = headers.length + 1;
    sheet.getRange(1, startCol, 1, RESULT_HEADERS.length)
      .setValues([RESULT_HEADERS]);
  }
}

// =============================================================
// 通知メール
// =============================================================

/**
 * 申請者に審査結果をメール通知。
 *
 * @param {Object} formData - 申請データ
 * @param {Object} result - 審査結果
 */
function sendNotificationEmail_(formData, result) {
  // メールアドレスは formData.purpose から抽出できないため
  // フォームの「メールアドレスを収集する」設定に依存
  const sheet = SpreadsheetApp.getActiveSpreadsheet()
    .getActiveSheet();
  const lastRow = sheet.getLastRow();

  // メールアドレス列（通常1列目）から取得
  const headers = sheet.getRange(
    1, 1, 1, sheet.getLastColumn()
  ).getValues()[0];
  const emailCol = headers.indexOf(FORM_FIELDS.email) + 1;

  if (emailCol === 0) {
    Logger.log('メールアドレス列が見つかりません');
    return;
  }

  const email = sheet.getRange(lastRow, emailCol).getValue();
  if (!email) {
    Logger.log('メールアドレスが空です');
    return;
  }

  const statusEmoji = {
    '承認': '✅',
    '却下': '❌',
    '要人間確認': '⚠️',
  };

  const emoji = statusEmoji[result.status] || '📋';
  const subject =
    emoji + ' 経費精算審査結果: ' + result.status;

  const body = [
    '経費精算の審査結果をお知らせします。',
    '',
    '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
    '■ 申請内容',
    '  申請種別: ' + formData.type,
    '  合計金額: ' + formData.amount.toLocaleString() + '円',
    '  参加人数: ' + formData.count + '人',
    '',
    '■ 審査結果',
    '  ステータス: ' + result.status,
    '  確信度: ' + result.confidence_score + ' / 5.0',
    '',
  ];

  if (result.rejection_reason) {
    body.push('■ 却下理由');
    body.push('  ' + result.rejection_reason);
    body.push('');
  }

  if (result.details) {
    body.push('■ 詳細');
    Object.keys(result.details).forEach(function(key) {
      body.push('  ' + key + ': ' + result.details[key]);
    });
    body.push('');
  }

  body.push('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  body.push('');
  body.push('※ このメールは自動送信されています。');
  body.push('※ ご不明点は経理部までお問い合わせください。');

  GmailApp.sendEmail(email, subject, body.join('\n'));
  Logger.log('通知メール送信完了: ' + email);
}

// =============================================================
// セットアップ・ユーティリティ
// =============================================================

/**
 * 初回セットアップ: フォーム送信トリガーを登録。
 * Apps Scriptエディタから手動で1回実行してください。
 */
function setupTrigger() {
  // 既存の onFormSubmit トリガーを削除
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(function(trigger) {
    if (trigger.getHandlerFunction() === 'onFormSubmit') {
      ScriptApp.deleteTrigger(trigger);
    }
  });

  // 新しいトリガーを作成
  ScriptApp.newTrigger('onFormSubmit')
    .forSpreadsheet(SpreadsheetApp.getActiveSpreadsheet())
    .onFormSubmit()
    .create();

  Logger.log('✅ onFormSubmitトリガーを登録しました');
}

/**
 * テスト用: APIの疎通確認。
 * 手動で実行してログを確認してください。
 */
function testApiConnection() {
  const config = getConfig_();
  Logger.log('API URL: ' + config.apiUrl);

  if (!config.apiUrl) {
    Logger.log(
      '❌ API_URLが未設定です。'
      + 'スクリプトプロパティに設定してください。'
    );
    return;
  }

  const testData = {
    type: '社内懇親会',
    amount: 24000,
    count: 6,
    participants_raw: '田中太郎、山田花子、佐藤一郎、鈴木次郎、高橋三郎、伊藤四郎',
    purpose: 'テスト送信（申請者: テスト太郎, 利用日: 2024-01-15）',
    receipt_url: null,
  };

  Logger.log('📤 テストリクエスト送信中...');
  const result = callExpenseCheckApi_(testData);
  Logger.log('📥 結果: ' + JSON.stringify(result, null, 2));
}
