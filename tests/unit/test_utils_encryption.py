import pytest
from unittest.mock import patch, MagicMock
from src.utils.encryption import TokenEncryption, get_encryption_key, create_token_encryptor


class TestTokenEncryption:
    """Test cases for TokenEncryption class."""
    
    def test_encrypt_decrypt_token(self):
        """Test token encryption and decryption."""
        encryption_key = "test-encryption-key-123"
        encryptor = TokenEncryption(encryption_key)
        
        original_token = "github_access_token_12345"
        
        # Encrypt the token
        encrypted_token = encryptor.encrypt_token(original_token)
        
        # Verify it's encrypted (different from original)
        assert encrypted_token != original_token
        assert isinstance(encrypted_token, str)
        
        # Decrypt the token
        decrypted_token = encryptor.decrypt_token(encrypted_token)
        
        # Verify it matches the original
        assert decrypted_token == original_token
    
    def test_encrypt_different_tokens_produce_different_results(self):
        """Test that different tokens produce different encrypted results."""
        encryption_key = "test-encryption-key-123"
        encryptor = TokenEncryption(encryption_key)
        
        token1 = "github_token_1"
        token2 = "github_token_2"
        
        encrypted1 = encryptor.encrypt_token(token1)
        encrypted2 = encryptor.encrypt_token(token2)
        
        assert encrypted1 != encrypted2
    
    def test_same_token_produces_different_encrypted_results(self):
        """Test that the same token produces different encrypted results each time."""
        encryption_key = "test-encryption-key-123"
        encryptor = TokenEncryption(encryption_key)
        
        token = "github_token_same"
        
        encrypted1 = encryptor.encrypt_token(token)
        encrypted2 = encryptor.encrypt_token(token)
        
        # Should be different due to random IV in Fernet
        assert encrypted1 != encrypted2
        
        # But both should decrypt to the same value
        assert encryptor.decrypt_token(encrypted1) == token
        assert encryptor.decrypt_token(encrypted2) == token
    
    def test_different_keys_produce_incompatible_encryption(self):
        """Test that different encryption keys are incompatible."""
        key1 = "encryption-key-1"
        key2 = "encryption-key-2"
        
        encryptor1 = TokenEncryption(key1)
        encryptor2 = TokenEncryption(key2)
        
        token = "test_token"
        encrypted_with_key1 = encryptor1.encrypt_token(token)
        
        # Attempting to decrypt with different key should fail
        with pytest.raises(Exception):
            encryptor2.decrypt_token(encrypted_with_key1)
    
    def test_invalid_encrypted_token_raises_exception(self):
        """Test that invalid encrypted token raises exception."""
        encryption_key = "test-encryption-key-123"
        encryptor = TokenEncryption(encryption_key)
        
        invalid_token = "invalid_encrypted_token"
        
        with pytest.raises(Exception):
            encryptor.decrypt_token(invalid_token)


class TestGetEncryptionKey:
    """Test cases for get_encryption_key function."""
    
    @patch.dict('os.environ', {'GITHUB_TOKEN_ENCRYPTION_KEY': 'env_key_123'})
    def test_get_key_from_environment(self):
        """Test getting encryption key from environment variable."""
        key = get_encryption_key()
        assert key == 'env_key_123'
    
    @patch.dict('os.environ', {}, clear=True)
    @patch('boto3.client')
    def test_get_key_from_parameter_store(self, mock_boto_client):
        """Test getting encryption key from AWS Parameter Store."""
        mock_ssm = MagicMock()
        mock_boto_client.return_value = mock_ssm
        mock_ssm.get_parameter.return_value = {
            'Parameter': {'Value': 'parameter_store_key_456'}
        }
        
        key = get_encryption_key()
        
        assert key == 'parameter_store_key_456'
        mock_ssm.get_parameter.assert_called_once_with(
            Name='/myfav-coworker/github-token-encryption-key',
            WithDecryption=True
        )
    
    @patch.dict('os.environ', {}, clear=True)
    @patch('boto3.client')
    def test_get_key_parameter_store_failure(self, mock_boto_client):
        """Test handling of Parameter Store failure."""
        mock_ssm = MagicMock()
        mock_boto_client.return_value = mock_ssm
        mock_ssm.get_parameter.side_effect = Exception("Parameter not found")
        
        with pytest.raises(RuntimeError, match="Failed to retrieve encryption key"):
            get_encryption_key()


class TestCreateTokenEncryptor:
    """Test cases for create_token_encryptor function."""
    
    @patch('src.utils.encryption.get_encryption_key')
    def test_create_token_encryptor(self, mock_get_key):
        """Test creating TokenEncryption instance."""
        mock_get_key.return_value = "test_key_789"
        
        encryptor = create_token_encryptor()
        
        assert isinstance(encryptor, TokenEncryption)
        mock_get_key.assert_called_once()
    
    @patch('src.utils.encryption.get_encryption_key')
    def test_create_token_encryptor_key_failure(self, mock_get_key):
        """Test handling of key retrieval failure."""
        mock_get_key.side_effect = RuntimeError("Key retrieval failed")
        
        with pytest.raises(RuntimeError, match="Key retrieval failed"):
            create_token_encryptor()
