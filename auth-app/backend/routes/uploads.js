const router = require('express').Router();
const { createClient } = require('@supabase/supabase-js');
const verifyToken = require('../middleware/verifyToken');
const multer = require('multer');
const { encryptFile, decryptFile, encryptMetadata, decryptMetadata, deriveKey, generateSalt } = require('../utils/encryption');

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 50 * 1024 * 1024 },
  fileFilter: (req, file, cb) => {
    const allowed = [
      'image/jpeg', 'image/png', 'image/webp',
      'application/pdf', 'text/plain',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ];
    allowed.includes(file.mimetype)
      ? cb(null, true)
      : cb(new Error('File type not allowed.'));
  },
});

// ── UPLOAD (with optional encryption) ────────────────────────────────────────
router.post('/', verifyToken, upload.single('file'), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file provided.' });

  const userId = req.user.id;
  const encrypt = req.body.encrypt === 'true' || req.body.encrypt === true;
  const userSecret = req.body.userSecret; // User's encryption secret (derived from password or OTP)
  
  let fileBuffer = req.file.buffer;
  let encryptionMetadata = {};
  let originalFilename = req.file.originalname;
  let storedFilename = originalFilename;

  // If encryption is requested, encrypt the file
  if (encrypt) {
    if (!userSecret) {
      return res.status(400).json({ error: 'Encryption requested but no userSecret provided.' });
    }

    try {
      // Encrypt the file content
      const { encryptedData, iv, tag, salt } = encryptFile(fileBuffer, userSecret);
      fileBuffer = encryptedData;
      
      // Encrypt the filename for additional privacy
      const filenameSalt = Buffer.from(salt, 'base64');
      const filenameKey = deriveKey(userSecret, filenameSalt);
      const { encrypted: encryptedFilename, iv: filenameIv, tag: filenameTag } = encryptMetadata(
        originalFilename,
        filenameKey
      );
      
      encryptionMetadata = {
        encrypted: true,
        encryption_iv: iv,
        encryption_tag: tag,
        encryption_salt: salt,
        encrypted_filename: encryptedFilename,
        filename_iv: filenameIv,
        filename_tag: filenameTag,
        requires_otp: true
      };
      
      // Use a generic filename for storage (hides original filename)
      storedFilename = `encrypted_${Date.now()}.enc`;
      
    } catch (error) {
      console.error('Encryption error:', error);
      return res.status(500).json({ error: 'File encryption failed.' });
    }
  }

  const filePath = `${userId}/${Date.now()}_${storedFilename}`;

  // Upload to Supabase Storage
  const { error: storageError } = await supabase.storage
    .from('user-files')
    .upload(filePath, fileBuffer, { 
      contentType: encrypt ? 'application/octet-stream' : req.file.mimetype 
    });

  if (storageError) {
    console.error('Storage upload error:', storageError);
    return res.status(500).json({ error: `Upload failed: ${storageError.message}` });
  }

  // Save file record with encryption metadata
  const { data, error: dbError } = await supabase
    .from('user_files')
    .insert({
      user_id: userId,
      file_name: encrypt ? 'encrypted_file' : originalFilename, // Hide real filename if encrypted
      file_path: filePath,
      file_size: fileBuffer.length,
      mime_type: encrypt ? 'application/octet-stream' : req.file.mimetype,
      ...encryptionMetadata
    })
    .select()
    .single();

  if (dbError) {
    console.error('DB insert error:', dbError);
    // Clean up uploaded file if DB insert fails
    await supabase.storage.from('user-files').remove([filePath]);
    return res.status(500).json({ error: `Failed to save file record: ${dbError.message}` });
  }

  // Log the upload
  await supabase.rpc('log_file_access', {
    p_user_id: userId,
    p_file_id: data.id,
    p_access_type: 'upload',
    p_otp_verified: false,
    p_ip_address: req.ip || req.connection.remoteAddress,
    p_user_agent: req.headers['user-agent'] || 'unknown',
    p_success: true
  });

  return res.status(201).json({ 
    message: encrypt ? 'File uploaded and encrypted.' : 'File uploaded.',
    file: {
      ...data,
      encrypted: encrypt,
      requires_otp: encrypt
    }
  });
});

// ── LIST ──────────────────────────────────────────────────────────────────────
router.get('/', verifyToken, async (req, res) => {
  const { data, error } = await supabase
    .from('user_files')
    .select('*')
    .eq('user_id', req.user.id)
    .order('uploaded_at', { ascending: false });

  if (error) return res.status(500).json({ error: 'Failed to fetch files.' });
  return res.json({ files: data });
});

// ── DELETE ────────────────────────────────────────────────────────────────────
router.delete('/:id', verifyToken, async (req, res) => {
  const { data: file } = await supabase
    .from('user_files')
    .select('*')
    .eq('id', req.params.id)
    .eq('user_id', req.user.id)
    .single();

  if (!file) return res.status(404).json({ error: 'File not found.' });

  await supabase.storage.from('user-files').remove([file.file_path]);
  await supabase.from('user_files').delete().eq('id', file.id);

  return res.json({ message: 'File deleted.' });
});

// ── REQUEST OTP FOR USER DOWNLOAD ────────────────────────────────────────────
router.post('/:id/request-download-otp', verifyToken, async (req, res) => {
  try {
    const userId = req.user.id;
    const fileId = req.params.id;
    
    // Get file metadata
    const { data: file, error: fileError } = await supabase
      .from('user_files')
      .select('*')
      .eq('id', fileId)
      .eq('user_id', userId)
      .single();
    
    if (fileError || !file) {
      return res.status(404).json({ error: 'File not found.' });
    }
    
    // Get user's phone number
    const { data: user, error: userError } = await supabase.auth.admin.getUserById(userId);
    
    if (userError || !user) {
      return res.status(404).json({ error: 'User not found.' });
    }
    
    const phone = user.user.phone;
    if (!phone) {
      return res.status(400).json({ 
        error: 'No phone number registered. Please add a phone number to your profile first.',
        requires_phone: true
      });
    }
    
    // Send OTP via Message Central
    const verificationId = await sendOtpViaMessageCentral(phone);
    
    if (!verificationId) {
      return res.status(500).json({ error: 'Failed to send OTP. Please try again.' });
    }
    
    // Store OTP verification record
    const expiresAt = new Date(Date.now() + 10 * 60 * 1000); // 10 minutes
    
    const { error: otpError } = await supabase
      .from('otp_verifications')
      .insert({
        user_id: userId,
        phone: phone,
        verification_id: verificationId,
        purpose: 'user_download',
        metadata: JSON.stringify({ file_id: fileId }),
        expires_at: expiresAt.toISOString(),
        attempts: 0
      });
    
    if (otpError) {
      console.error('OTP storage error:', otpError);
      return res.status(500).json({ error: 'Failed to store OTP verification.' });
    }
    
    console.log(`[user/download-otp] OTP sent to user ${userId} for file ${fileId}`);
    
    return res.json({ 
      message: 'OTP sent to your registered phone number.',
      phone_last_4: phone.slice(-4),
      expires_in_minutes: 10,
      file_name: file.file_name
    });
  } catch (error) {
    console.error('[user/download-otp] ERROR:', error);
    return res.status(500).json({ error: error.message || 'Failed to request OTP.' });
  }
});

// ── DOWNLOAD FILE WITH OTP VERIFICATION ───────────────────────────────────────
router.post('/:id/download', verifyToken, async (req, res) => {
  try {
    const { otp } = req.body;
    const userId = req.user.id;
    const fileId = req.params.id;
    
    if (!otp || !/^\d{6}$/.test(otp.trim())) {
      return res.status(400).json({ error: 'Valid 6-digit OTP required.' });
    }
    
    // Get file metadata
    const { data: file, error: fileError } = await supabase
      .from('user_files')
      .select('*')
      .eq('id', fileId)
      .eq('user_id', userId)
      .single();
    
    if (fileError || !file) {
      return res.status(404).json({ error: 'File not found.' });
    }
    
    // Get pending OTP verification for this file
    const { data: otpRecord, error: otpError } = await supabase
      .from('otp_verifications')
      .select('*')
      .eq('user_id', userId)
      .eq('purpose', 'user_download')
      .eq('verified', false)
      .gte('expires_at', new Date().toISOString())
      .order('created_at', { ascending: false })
      .limit(1)
      .single();
    
    if (otpError || !otpRecord) {
      return res.status(401).json({ error: 'No pending OTP found or OTP expired. Please request a new one.' });
    }
    
    // Verify the OTP is for this file
    try {
      const metadata = JSON.parse(otpRecord.metadata || '{}');
      if (metadata.file_id !== fileId) {
        return res.status(401).json({ error: 'OTP is not valid for this file.' });
      }
    } catch (e) {
      console.error('Metadata parse error:', e);
    }
    
    // Check attempt limit
    const MAX_ATTEMPTS = 5;
    if (otpRecord.attempts >= MAX_ATTEMPTS) {
      await supabase
        .from('otp_verifications')
        .delete()
        .eq('id', otpRecord.id);
      
      return res.status(429).json({ 
        error: 'Too many failed attempts. Please request a new OTP.' 
      });
    }
    
    // Verify OTP with Message Central
    const valid = await verifyOtpWithMessageCentral(otpRecord.verification_id, otp.trim());
    
    if (!valid) {
      // Increment failed attempts
      await supabase
        .from('otp_verifications')
        .update({ 
          attempts: otpRecord.attempts + 1,
          last_attempt_at: new Date().toISOString()
        })
        .eq('id', otpRecord.id);
      
      const remainingAttempts = MAX_ATTEMPTS - (otpRecord.attempts + 1);
      
      if (remainingAttempts <= 0) {
        await supabase
          .from('otp_verifications')
          .delete()
          .eq('id', otpRecord.id);
        
        return res.status(429).json({ 
          error: 'Too many failed attempts. Please request a new OTP.' 
        });
      }
      
      // Log failed attempt
      await supabase.rpc('log_file_access', {
        p_user_id: userId,
        p_file_id: fileId,
        p_access_type: 'download',
        p_otp_verified: false,
        p_ip_address: req.ip || req.connection.remoteAddress,
        p_user_agent: req.headers['user-agent'] || 'unknown',
        p_success: false,
        p_error_message: 'Invalid OTP'
      });
      
      return res.status(401).json({ 
        error: `Invalid OTP. ${remainingAttempts} attempt(s) remaining.`,
        remaining_attempts: remainingAttempts
      });
    }
    
    // OTP is valid - mark as verified
    await supabase
      .from('otp_verifications')
      .update({ 
        verified: true, 
        verified_at: new Date().toISOString() 
      })
      .eq('id', otpRecord.id);
    
    // Download file from storage
    const { data: fileData, error: downloadError } = await supabase.storage
      .from('user-files')
      .download(file.file_path);
    
    if (downloadError) {
      console.error('Download error:', downloadError);
      
      await supabase.rpc('log_file_access', {
        p_user_id: userId,
        p_file_id: fileId,
        p_access_type: 'download',
        p_otp_verified: true,
        p_ip_address: req.ip || req.connection.remoteAddress,
        p_user_agent: req.headers['user-agent'] || 'unknown',
        p_success: false,
        p_error_message: downloadError.message
      });
      
      return res.status(500).json({ error: 'Failed to download file.' });
    }
    
    // Convert Blob to Buffer
    const arrayBuffer = await fileData.arrayBuffer();
    const fileBuffer = Buffer.from(arrayBuffer);
    
    // Log successful download
    await supabase.rpc('log_file_access', {
      p_user_id: userId,
      p_file_id: fileId,
      p_access_type: 'download',
      p_otp_verified: true,
      p_ip_address: req.ip || req.connection.remoteAddress,
      p_user_agent: req.headers['user-agent'] || 'unknown',
      p_success: true
    });
    
    console.log(`[user/download] User ${userId} downloaded file ${fileId} with OTP verification`);
    
    // Return file
    res.setHeader('Content-Type', file.mime_type || 'application/octet-stream');
    res.setHeader('Content-Disposition', `attachment; filename="${file.file_name}"`);
    res.send(fileBuffer);
    
  } catch (error) {
    console.error('[user/download] ERROR:', error);
    return res.status(500).json({ error: error.message || 'Download failed.' });
  }
});

// ── SIGNED URL (DEPRECATED - Use OTP download instead) ───────────────────────
router.get('/:id/url', verifyToken, async (req, res) => {
  // This endpoint is deprecated in favor of OTP-protected download
  // Keeping for backward compatibility but should redirect to OTP flow
  
  const { data: file } = await supabase
    .from('user_files')
    .select('*')
    .eq('id', req.params.id)
    .eq('user_id', req.user.id)
    .single();

  if (!file) return res.status(404).json({ error: 'File not found.' });

  // Always require OTP for downloads
  return res.status(403).json({ 
    error: 'OTP verification required to download files.',
    requires_otp: true,
    file_id: file.id,
    message: 'Please use POST /:id/request-download-otp to request OTP, then POST /:id/download with OTP to download.'
  });
});

// ── DECRYPT FILE (requires OTP verification) ──────────────────────────────────
router.post('/:id/decrypt', verifyToken, async (req, res) => {
  const { otp, userSecret } = req.body;

  if (!otp) {
    return res.status(400).json({ error: 'OTP required for decryption.' });
  }

  if (!userSecret) {
    return res.status(400).json({ error: 'User secret required for decryption.' });
  }

  // Get file metadata
  const { data: file } = await supabase
    .from('user_files')
    .select('*')
    .eq('id', req.params.id)
    .eq('user_id', req.user.id)
    .single();

  if (!file) {
    return res.status(404).json({ error: 'File not found.' });
  }

  if (!file.encrypted) {
    return res.status(400).json({ error: 'File is not encrypted.' });
  }

  // Verify OTP
  // TODO: Integrate with actual OTP verification service
  // For now, we'll simulate OTP verification
  const otpValid = await verifyOTP(req.user.id, otp);
  
  if (!otpValid) {
    await supabase.rpc('log_file_access', {
      p_user_id: req.user.id,
      p_file_id: file.id,
      p_access_type: 'decrypt',
      p_otp_verified: false,
      p_ip_address: req.ip || req.connection.remoteAddress,
      p_user_agent: req.headers['user-agent'] || 'unknown',
      p_success: false,
      p_error_message: 'Invalid OTP'
    });
    return res.status(403).json({ error: 'Invalid OTP.' });
  }

  try {
    // Download encrypted file from storage
    const { data: fileData, error: downloadError } = await supabase.storage
      .from('user-files')
      .download(file.file_path);

    if (downloadError) {
      throw new Error(`Download failed: ${downloadError.message}`);
    }

    // Convert Blob to Buffer
    const arrayBuffer = await fileData.arrayBuffer();
    const encryptedBuffer = Buffer.from(arrayBuffer);

    // Decrypt the file
    const decryptedBuffer = decryptFile(
      encryptedBuffer,
      userSecret,
      file.encryption_iv,
      file.encryption_tag,
      file.encryption_salt
    );

    // Decrypt the filename
    const filenameSalt = Buffer.from(file.encryption_salt, 'base64');
    const filenameKey = deriveKey(userSecret, filenameSalt);
    const originalFilename = decryptMetadata(
      file.encrypted_filename,
      filenameKey,
      file.filename_iv,
      file.filename_tag
    );

    // Log successful decryption
    await supabase.rpc('log_file_access', {
      p_user_id: req.user.id,
      p_file_id: file.id,
      p_access_type: 'decrypt',
      p_otp_verified: true,
      p_ip_address: req.ip || req.connection.remoteAddress,
      p_user_agent: req.headers['user-agent'] || 'unknown',
      p_success: true
    });

    // Return decrypted file
    res.setHeader('Content-Disposition', `attachment; filename="${originalFilename}"`);
    res.setHeader('Content-Type', 'application/octet-stream');
    res.send(decryptedBuffer);

  } catch (error) {
    console.error('Decryption error:', error);
    
    await supabase.rpc('log_file_access', {
      p_user_id: req.user.id,
      p_file_id: file.id,
      p_access_type: 'decrypt',
      p_otp_verified: true,
      p_ip_address: req.ip || req.connection.remoteAddress,
      p_user_agent: req.headers['user-agent'] || 'unknown',
      p_success: false,
      p_error_message: error.message
    });

    return res.status(500).json({ error: 'Decryption failed. Invalid secret or corrupted file.' });
  }
});

// ── REQUEST OTP FOR FILE ACCESS ───────────────────────────────────────────────
router.post('/:id/request-otp', verifyToken, async (req, res) => {
  const { data: file } = await supabase
    .from('user_files')
    .select('id, encrypted, requires_otp')
    .eq('id', req.params.id)
    .eq('user_id', req.user.id)
    .single();

  if (!file) {
    return res.status(404).json({ error: 'File not found.' });
  }

  if (!file.encrypted || !file.requires_otp) {
    return res.status(400).json({ error: 'File does not require OTP.' });
  }

  // Generate and send OTP
  // TODO: Integrate with actual OTP service (Twilio, AWS SNS, etc.)
  const otpSent = await sendOTP(req.user.id);

  if (!otpSent) {
    return res.status(500).json({ error: 'Failed to send OTP.' });
  }

  return res.json({ 
    message: 'OTP sent successfully.',
    file_id: file.id
  });
});

// ── GET FILE ACCESS LOGS ──────────────────────────────────────────────────────
router.get('/:id/access-logs', verifyToken, async (req, res) => {
  const { data: logs, error } = await supabase
    .from('file_access_logs')
    .select('*')
    .eq('file_id', req.params.id)
    .eq('user_id', req.user.id)
    .order('accessed_at', { ascending: false })
    .limit(50);

  if (error) {
    return res.status(500).json({ error: 'Failed to fetch access logs.' });
  }

  return res.json({ logs });
});

// ── GET USER ACCESS STATISTICS ────────────────────────────────────────────────
router.get('/stats/access', verifyToken, async (req, res) => {
  const { data, error } = await supabase
    .rpc('get_file_access_stats', { p_user_id: req.user.id });

  if (error) {
    return res.status(500).json({ error: 'Failed to fetch statistics.' });
  }

  return res.json({ stats: data[0] || {} });
});

// ── AGENT DOCUMENT ACCESS (requires OTP) ──────────────────────────────────────
router.post('/agent/request-access', verifyToken, async (req, res) => {
  try {
    const userId = req.user.id;
    
    // Check if user has uploaded documents
    const { data: files, error: filesError } = await supabase
      .from('user_files')
      .select('id, file_name, uploaded_at')
      .eq('user_id', userId)
      .order('uploaded_at', { ascending: false });
    
    if (filesError) {
      return res.status(500).json({ error: 'Failed to fetch files.' });
    }
    
    if (!files || files.length === 0) {
      return res.status(404).json({ error: 'No documents found.' });
    }
    
    // Get user's phone number
    const { data: user, error: userError } = await supabase.auth.admin.getUserById(userId);
    
    if (userError || !user) {
      return res.status(404).json({ error: 'User not found.' });
    }
    
    const phone = user.user.phone;
    if (!phone) {
      return res.status(400).json({ 
        error: 'No phone number registered. Please add a phone number to your profile first.',
        requires_phone: true
      });
    }
    
    // Send OTP via Message Central
    const verificationId = await sendOtpViaMessageCentral(phone);
    
    if (!verificationId) {
      return res.status(500).json({ error: 'Failed to send OTP. Please try again.' });
    }
    
    // Store OTP verification record
    const expiresAt = new Date(Date.now() + 10 * 60 * 1000); // 10 minutes
    
    const { error: otpError } = await supabase
      .from('otp_verifications')
      .insert({
        user_id: userId,
        phone: phone,
        verification_id: verificationId,
        purpose: 'agent_document_access',
        expires_at: expiresAt.toISOString(),
        attempts: 0
      });
    
    if (otpError) {
      console.error('OTP storage error:', otpError);
      return res.status(500).json({ error: 'Failed to store OTP verification.' });
    }
    
    console.log(`[agent/request-access] OTP sent to user ${userId} at ${phone}`);
    
    return res.json({ 
      message: 'OTP sent to your registered phone number.',
      phone_last_4: phone.slice(-4),
      expires_in_minutes: 10,
      file_count: files.length
    });
  } catch (error) {
    console.error('[agent/request-access] ERROR:', error);
    return res.status(500).json({ error: error.message || 'Failed to request document access.' });
  }
});

// ── AGENT VERIFY OTP AND GET DOCUMENTS ────────────────────────────────────────
router.post('/agent/verify-and-access', verifyToken, async (req, res) => {
  try {
    const { otp } = req.body;
    const userId = req.user.id;
    
    if (!otp || !/^\d{6}$/.test(otp.trim())) {
      return res.status(400).json({ error: 'Valid 6-digit OTP required.' });
    }
    
    // Get pending OTP verification
    const { data: otpRecord, error: otpError } = await supabase
      .from('otp_verifications')
      .select('*')
      .eq('user_id', userId)
      .eq('purpose', 'agent_document_access')
      .eq('verified', false)
      .gte('expires_at', new Date().toISOString())
      .order('created_at', { ascending: false })
      .limit(1)
      .single();
    
    if (otpError || !otpRecord) {
      return res.status(401).json({ error: 'No pending OTP found or OTP expired. Please request a new one.' });
    }
    
    // Check attempt limit
    const MAX_ATTEMPTS = 5;
    if (otpRecord.attempts >= MAX_ATTEMPTS) {
      await supabase
        .from('otp_verifications')
        .delete()
        .eq('id', otpRecord.id);
      
      return res.status(429).json({ 
        error: 'Too many failed attempts. Please request a new OTP.' 
      });
    }
    
    // Verify OTP with Message Central
    const valid = await verifyOtpWithMessageCentral(otpRecord.verification_id, otp.trim());
    
    if (!valid) {
      // Increment failed attempts
      await supabase
        .from('otp_verifications')
        .update({ 
          attempts: otpRecord.attempts + 1,
          last_attempt_at: new Date().toISOString()
        })
        .eq('id', otpRecord.id);
      
      const remainingAttempts = MAX_ATTEMPTS - (otpRecord.attempts + 1);
      
      if (remainingAttempts <= 0) {
        await supabase
          .from('otp_verifications')
          .delete()
          .eq('id', otpRecord.id);
        
        return res.status(429).json({ 
          error: 'Too many failed attempts. Please request a new OTP.' 
        });
      }
      
      return res.status(401).json({ 
        error: `Invalid OTP. ${remainingAttempts} attempt(s) remaining.`,
        remaining_attempts: remainingAttempts
      });
    }
    
    // OTP is valid - mark as verified
    await supabase
      .from('otp_verifications')
      .update({ 
        verified: true, 
        verified_at: new Date().toISOString() 
      })
      .eq('id', otpRecord.id);
    
    // Get all user documents
    const { data: files, error: filesError } = await supabase
      .from('user_files')
      .select('*')
      .eq('user_id', userId)
      .order('uploaded_at', { ascending: false });
    
    if (filesError) {
      return res.status(500).json({ error: 'Failed to fetch documents.' });
    }
    
    // Log successful access
    for (const file of files) {
      await supabase.rpc('log_file_access', {
        p_user_id: userId,
        p_file_id: file.id,
        p_access_type: 'agent_access',
        p_otp_verified: true,
        p_ip_address: req.ip || req.connection.remoteAddress,
        p_user_agent: 'agent',
        p_success: true
      });
    }
    
    console.log(`[agent/verify-and-access] User ${userId} granted agent access to ${files.length} documents`);
    
    // Return document metadata (not the actual files, agent will request them separately)
    const documentList = files.map(f => ({
      id: f.id,
      file_name: f.file_name,
      file_size: f.file_size,
      mime_type: f.mime_type,
      uploaded_at: f.uploaded_at,
      encrypted: f.encrypted || false
    }));
    
    return res.json({ 
      message: 'OTP verified successfully. Agent can now access your documents.',
      verified: true,
      documents: documentList,
      access_granted_at: new Date().toISOString(),
      access_expires_at: new Date(Date.now() + 30 * 60 * 1000).toISOString() // 30 minutes
    });
  } catch (error) {
    console.error('[agent/verify-and-access] ERROR:', error);
    return res.status(500).json({ error: error.message || 'Verification failed.' });
  }
});

// ── AGENT GET DOCUMENT CONTENT (after OTP verification) ───────────────────────
router.get('/agent/document/:id', verifyToken, async (req, res) => {
  try {
    const userId = req.user.id;
    const fileId = req.params.id;
    
    // Check if user has a recent verified OTP for agent access
    const { data: otpRecord, error: otpError } = await supabase
      .from('otp_verifications')
      .select('*')
      .eq('user_id', userId)
      .eq('purpose', 'agent_document_access')
      .eq('verified', true)
      .gte('verified_at', new Date(Date.now() - 30 * 60 * 1000).toISOString()) // Within last 30 minutes
      .order('verified_at', { ascending: false })
      .limit(1)
      .single();
    
    if (otpError || !otpRecord) {
      return res.status(403).json({ 
        error: 'OTP verification required or expired. Please verify OTP first.',
        requires_otp: true
      });
    }
    
    // Get file metadata
    const { data: file, error: fileError } = await supabase
      .from('user_files')
      .select('*')
      .eq('id', fileId)
      .eq('user_id', userId)
      .single();
    
    if (fileError || !file) {
      return res.status(404).json({ error: 'Document not found.' });
    }
    
    // Download file from storage
    const { data: fileData, error: downloadError } = await supabase.storage
      .from('user-files')
      .download(file.file_path);
    
    if (downloadError) {
      console.error('Download error:', downloadError);
      return res.status(500).json({ error: 'Failed to download document.' });
    }
    
    // Convert Blob to Buffer
    const arrayBuffer = await fileData.arrayBuffer();
    const fileBuffer = Buffer.from(arrayBuffer);
    
    // Log access
    await supabase.rpc('log_file_access', {
      p_user_id: userId,
      p_file_id: file.id,
      p_access_type: 'agent_download',
      p_otp_verified: true,
      p_ip_address: req.ip || req.connection.remoteAddress,
      p_user_agent: 'agent',
      p_success: true
    });
    
    // Return file
    res.setHeader('Content-Type', file.mime_type || 'application/octet-stream');
    res.setHeader('Content-Disposition', `inline; filename="${file.file_name}"`);
    res.send(fileBuffer);
    
  } catch (error) {
    console.error('[agent/document] ERROR:', error);
    return res.status(500).json({ error: error.message || 'Failed to access document.' });
  }
});

// ── HELPER FUNCTIONS ──────────────────────────────────────────────────────────

/**
 * Verify OTP for file access using Message Central
 */
async function verifyOTP(userId, otp) {
  try {
    // Get user's phone number from Supabase
    const { data: user, error: userError } = await supabase.auth.admin.getUserById(userId);
    
    if (userError || !user) {
      console.error('User not found:', userError);
      return false;
    }

    const phone = user.user.phone;
    if (!phone) {
      console.error('User has no phone number registered');
      return false;
    }

    // Check if there's a pending OTP verification for this user
    const { data: otpRecord, error: otpError } = await supabase
      .from('otp_verifications')
      .select('*')
      .eq('user_id', userId)
      .eq('purpose', 'file_access')
      .eq('verified', false)
      .gte('expires_at', new Date().toISOString())
      .order('created_at', { ascending: false })
      .limit(1)
      .single();

    if (otpError || !otpRecord) {
      console.error('No pending OTP found:', otpError);
      return false;
    }

    // Verify OTP with Message Central
    const valid = await verifyOtpWithMessageCentral(otpRecord.verification_id, otp);
    
    if (!valid) {
      // Increment failed attempts
      await supabase
        .from('otp_verifications')
        .update({ 
          attempts: (otpRecord.attempts || 0) + 1,
          last_attempt_at: new Date().toISOString()
        })
        .eq('id', otpRecord.id);
      
      return false;
    }

    // Mark OTP as verified
    await supabase
      .from('otp_verifications')
      .update({ 
        verified: true, 
        verified_at: new Date().toISOString() 
      })
      .eq('id', otpRecord.id);

    return true;
  } catch (error) {
    console.error('OTP verification error:', error);
    return false;
  }
}

/**
 * Send OTP to user via Message Central
 */
async function sendOTP(userId) {
  try {
    // Get user's phone number from Supabase
    const { data: user, error: userError } = await supabase.auth.admin.getUserById(userId);
    
    if (userError || !user) {
      console.error('User not found:', userError);
      return false;
    }

    const phone = user.user.phone;
    if (!phone) {
      console.error('User has no phone number registered');
      return false;
    }

    // Send OTP via Message Central
    const verificationId = await sendOtpViaMessageCentral(phone);
    
    if (!verificationId) {
      return false;
    }

    // Store OTP verification record
    const expiresAt = new Date(Date.now() + 10 * 60 * 1000); // 10 minutes

    const { error } = await supabase
      .from('otp_verifications')
      .insert({
        user_id: userId,
        phone: phone,
        verification_id: verificationId,
        purpose: 'file_access',
        expires_at: expiresAt.toISOString(),
        attempts: 0
      });

    if (error) {
      console.error('OTP storage error:', error);
      return false;
    }

    console.log(`OTP sent to user ${userId} at ${phone}`);
    return true;
  } catch (error) {
    console.error('OTP generation error:', error);
    return false;
  }
}

/**
 * Send OTP via Message Central API
 */
async function sendOtpViaMessageCentral(phone) {
  try {
    const BASE_URL = 'https://cpaas.messagecentral.com';
    const CUSTOMER_ID = process.env.MC_CUSTOMER_ID;
    const PASSWORD_B64 = process.env.MC_PASSWORD_B64;

    if (!CUSTOMER_ID || !PASSWORD_B64) {
      throw new Error('Message Central credentials not configured');
    }

    // Get auth token
    const authUrl = `${BASE_URL}/auth/v1/authentication/token?customerId=${CUSTOMER_ID}&key=${PASSWORD_B64}&scope=NEW&country=91`;
    const authRes = await fetch(authUrl, { headers: { accept: '*/*' } });
    
    if (!authRes.ok) {
      throw new Error(`Message Central auth failed: ${authRes.status}`);
    }
    
    const authData = await authRes.json();
    const token = authData.token;

    if (!token) {
      throw new Error('Failed to get auth token from Message Central');
    }

    // Send OTP
    const number = phone.replace(/^\+91/, '').replace(/^\+/, '');
    const sendUrl = `${BASE_URL}/verification/v3/send?countryCode=91&flowType=SMS&mobileNumber=${number}&otpLength=6`;
    
    const sendRes = await fetch(sendUrl, {
      method: 'POST',
      headers: { authToken: token }
    });
    
    if (!sendRes.ok) {
      throw new Error(`Message Central send failed: ${sendRes.status}`);
    }
    
    const sendData = await sendRes.json();
    
    if (sendData.responseCode !== 200 || !sendData.data?.verificationId) {
      throw new Error(`MC error: ${sendData.message || 'No verificationId'}`);
    }
    
    return sendData.data.verificationId;
  } catch (error) {
    console.error('Message Central send error:', error);
    return null;
  }
}

/**
 * Verify OTP with Message Central API
 */
async function verifyOtpWithMessageCentral(verificationId, otp) {
  try {
    const BASE_URL = 'https://cpaas.messagecentral.com';
    const CUSTOMER_ID = process.env.MC_CUSTOMER_ID;
    const PASSWORD_B64 = process.env.MC_PASSWORD_B64;

    if (!CUSTOMER_ID || !PASSWORD_B64) {
      throw new Error('Message Central credentials not configured');
    }

    // Get auth token
    const authUrl = `${BASE_URL}/auth/v1/authentication/token?customerId=${CUSTOMER_ID}&key=${PASSWORD_B64}&scope=NEW&country=91`;
    const authRes = await fetch(authUrl, { headers: { accept: '*/*' } });
    
    if (!authRes.ok) {
      throw new Error(`Message Central auth failed: ${authRes.status}`);
    }
    
    const authData = await authRes.json();
    const token = authData.token;

    if (!token) {
      throw new Error('Failed to get auth token from Message Central');
    }

    // Verify OTP
    const verifyUrl = `${BASE_URL}/verification/v3/validateOtp?verificationId=${verificationId}&code=${otp}`;
    
    const verifyRes = await fetch(verifyUrl, { 
      headers: { authToken: token } 
    });
    
    if (!verifyRes.ok) {
      console.error(`Message Central verify failed: ${verifyRes.status}`);
      return false;
    }
    
    const verifyData = await verifyRes.json();
    
    return verifyData?.data?.verificationStatus === 'VERIFICATION_COMPLETED';
  } catch (error) {
    console.error('Message Central verify error:', error);
    return false;
  }
}

module.exports = router;