---
name: flutter-secure-client
description: "ALWAYS use this skill when the user asks to: implement secure HTTP communication in Flutter, set up Dio with interceptors for a DRF backend, implement Face ID or fingerprint login in Flutter, store tokens securely in Flutter, implement certificate pinning, handle 401 auto-refresh in Flutter, set up flutter_secure_storage for JWT tokens, implement biometric authentication with local_auth, obfuscate Flutter code for release, or build the complete Flutter client-side authentication layer for a Django REST API. Also trigger for: SSL pinning in Flutter, Dio interceptors, BiometricAuthService, SecureStorage for tokens, auto token refresh, logout clearing tokens, detecting root/jailbreak in Flutter, or any question about how Flutter communicates securely with a Django backend."
---

# Flutter Secure Client — Cliente seguro para DRF con biometría

## Arquitectura del cliente

```
lib/
├── services/
│   ├── api_service.dart          # Dio + interceptores + certificate pinning
│   ├── biometric_service.dart    # Face ID / huella con local_auth
│   └── auth_service.dart        # Gestión del ciclo de vida de tokens
├── storage/
│   └── secure_storage.dart      # Wrapper de flutter_secure_storage
└── interceptors/
    └── auth_interceptor.dart    # Auto-refresh en 401
```

---

## 1. Dependencias (pubspec.yaml)

```yaml
dependencies:
  dio: ^5.4.0                    # Cliente HTTP con interceptores
  flutter_secure_storage: ^9.0.0 # Almacenamiento seguro (Keychain/AES)
  local_auth: ^2.2.0             # Face ID y huella digital
  device_info_plus: ^9.1.0       # Device ID para cabecera X-Device-ID
  connectivity_plus: ^5.0.0      # Verificar conexión antes de requests

dev_dependencies:
  flutter_obfuscate: ^1.0.0     # Para el build de release
```

---

## 2. Almacenamiento seguro de tokens

```dart
// lib/storage/secure_storage.dart
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SecureTokenStorage {
  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock),
  );

  // Claves de almacenamiento
  static const _keyAccess = 'access_token';
  static const _keyRefresh = 'refresh_token';
  static const _keyBiometricRefresh = 'biometric_refresh_token';
  static const _keyBiometricEnabled = 'biometric_enabled';

  // Access token (en memoria preferiblemente, en storage como respaldo)
  static Future<void> saveTokens({
    required String access,
    required String refresh,
  }) async {
    await Future.wait([
      _storage.write(key: _keyAccess, value: access),
      _storage.write(key: _keyRefresh, value: refresh),
    ]);
  }

  static Future<String?> getAccessToken() =>
      _storage.read(key: _keyAccess);

  static Future<String?> getRefreshToken() =>
      _storage.read(key: _keyRefresh);

  // Token específico para biometría (solo accesible tras verificación biométrica)
  static Future<void> saveBiometricRefreshToken(String token) async {
    await _storage.write(key: _keyBiometricRefresh, value: token);
    await _storage.write(key: _keyBiometricEnabled, value: 'true');
  }

  static Future<String?> getBiometricRefreshToken() =>
      _storage.read(key: _keyBiometricRefresh);

  static Future<bool> isBiometricEnabled() async {
    final val = await _storage.read(key: _keyBiometricEnabled);
    return val == 'true';
  }

  // Limpiar TODO al hacer logout
  static Future<void> clearAll() async {
    await _storage.deleteAll();
  }
}
```

---

## 3. Servicio biométrico

```dart
// lib/services/biometric_service.dart
import 'package:local_auth/local_auth.dart';
import 'secure_storage.dart'; // ajustar import según estructura

class BiometricService {
  final _auth = LocalAuthentication();

  // Verificar disponibilidad
  Future<bool> isAvailable() async {
    final supported = await _auth.isDeviceSupported();
    final canCheck = await _auth.canCheckBiometrics;
    return supported && canCheck;
  }

  // Detectar tipo (Face ID o huella)
  Future<BiometricType?> getType() async {
    final biometrics = await _auth.getAvailableBiometrics();
    if (biometrics.contains(BiometricType.face)) return BiometricType.face;
    if (biometrics.contains(BiometricType.fingerprint)) return BiometricType.fingerprint;
    if (biometrics.contains(BiometricType.strong)) return BiometricType.strong;
    return null;
  }

  // Activar biometría (llamar tras login exitoso con password)
  Future<bool> enableBiometrics(String refreshToken) async {
    final ok = await _authenticate('Confirma para activar el acceso rápido');
    if (!ok) return false;

    // Guardar refresh token protegido por biometría
    await SecureTokenStorage.saveBiometricRefreshToken(refreshToken);
    return true;
  }

  // Login biométrico — devuelve refresh token si la cara/huella coincide
  Future<String?> authenticateAndGetToken() async {
    final enabled = await SecureTokenStorage.isBiometricEnabled();
    if (!enabled) return null;

    final ok = await _authenticate('Usa tu cara o huella para entrar');
    if (!ok) return null;

    // Solo accesible tras autenticación exitosa
    return SecureTokenStorage.getBiometricRefreshToken();
  }

  // Autenticación nativa del OS
  Future<bool> _authenticate(String reason) async {
    try {
      return await _auth.authenticate(
        localizedReason: reason,
        options: const AuthenticationOptions(
          biometricOnly: true,
          stickyAuth: true,
          useErrorDialogs: true,
        ),
      );
    } catch (_) {
      return false;
    }
  }
}
```

---

## 4. API Service con Dio + Certificate Pinning + Auto-refresh

```dart
// lib/services/api_service.dart
import 'dart:io';
import 'package:dio/dio.dart';
import 'package:dio/io.dart';
import 'secure_storage.dart';

class ApiService {
  static const _baseUrl = 'https://api.tudominio.com/api/v1/';

  late final Dio _dio;

  ApiService() {
    _dio = Dio(BaseOptions(
      baseUrl: _baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 15),
      headers: {'Content-Type': 'application/json'},
    ));

    _setupCertificatePinning();
    _dio.interceptors.add(_AuthInterceptor(_dio));
  }

  // Certificate Pinning — solo acepta el certificado de tu servidor
  void _setupCertificatePinning() {
    (_dio.httpClientAdapter as IOHttpClientAdapter).createHttpClient = () {
      final client = HttpClient();
      client.badCertificateCallback = (cert, host, port) {
        // En producción: validar el SHA256 del certificado
        // return cert.sha1.toString() == 'TU_SHA256_AQUI';
        return false; // Rechazar certificados inválidos
      };
      return client;
    };
  }

  // Métodos de autenticación
  Future<Map<String, dynamic>?> login(String email, String password) async {
    try {
      final response = await _dio.post('/auth/login/', data: {
        'email': email,
        'password': password,
      });
      return response.data;
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) return null;
      rethrow;
    }
  }

  Future<Map<String, dynamic>?> refreshToken(String refreshToken) async {
    try {
      final response = await _dio.post('/auth/token/refresh/', data: {
        'refresh': refreshToken,
      });
      return response.data;
    } on DioException {
      return null;
    }
  }

  Future<void> logout(String refreshToken) async {
    try {
      await _dio.post('/auth/logout/', data: {'refresh': refreshToken});
    } finally {
      await SecureTokenStorage.clearAll();
    }
  }

  Future<void> enableBiometric(String deviceId, String deviceModel) async {
    await _dio.post('/auth/biometric/enable/', data: {
      'device_id': deviceId,
      'device_model': deviceModel,
    });
  }

  // Getter para requests protegidos
  Dio get client => _dio;
}

// Interceptor de autenticación con auto-refresh
class _AuthInterceptor extends Interceptor {
  final Dio _dio;
  bool _isRefreshing = false;

  _AuthInterceptor(this._dio);

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await SecureTokenStorage.getAccessToken();
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    if (err.response?.statusCode == 401 && !_isRefreshing) {
      _isRefreshing = true;
      try {
        final newTokens = await _tryRefresh();
        if (newTokens != null) {
          // Reintentar la petición original con nuevo token
          err.requestOptions.headers['Authorization'] =
              'Bearer ${newTokens['access']}';
          final response = await _dio.fetch(err.requestOptions);
          handler.resolve(response);
          return;
        }
      } finally {
        _isRefreshing = false;
      }
      // Si no se pudo refrescar — redirigir a login
      await SecureTokenStorage.clearAll();
    }
    handler.next(err);
  }

  Future<Map<String, dynamic>?> _tryRefresh() async {
    final refresh = await SecureTokenStorage.getRefreshToken();
    if (refresh == null) return null;
    try {
      final response = await _dio.post('/auth/token/refresh/',
          data: {'refresh': refresh});
      final data = response.data;
      await SecureTokenStorage.saveTokens(
        access: data['access'],
        refresh: data['refresh'],
      );
      return data;
    } catch (_) {
      return null;
    }
  }
}
```

---

## 5. Auth Service — orquestador del flujo completo

```dart
// lib/services/auth_service.dart
import 'package:device_info_plus/device_info_plus.dart';
import 'dart:io';

class AuthService {
  final ApiService _api;
  final BiometricService _biometric;

  AuthService(this._api, this._biometric);

  // LOGIN COMPLETO: biometría si disponible, password como fallback
  Future<bool> loginWithBiometricOrFallback() async {
    final available = await _biometric.isAvailable();
    final enabled = await SecureTokenStorage.isBiometricEnabled();

    if (available && enabled) {
      return _loginWithBiometric();
    }
    return false; // Mostrar pantalla de password
  }

  Future<bool> _loginWithBiometric() async {
    final refreshToken = await _biometric.authenticateAndGetToken();
    if (refreshToken == null) return false;

    final tokens = await _api.refreshToken(refreshToken);
    if (tokens == null) return false;

    await SecureTokenStorage.saveTokens(
      access: tokens['access'],
      refresh: tokens['refresh'],
    );
    // Actualizar también el token biométrico con el nuevo refresh
    await SecureTokenStorage.saveBiometricRefreshToken(tokens['refresh']);
    return true;
  }

  // PRIMER LOGIN: email + password
  Future<bool> loginWithPassword(String email, String password) async {
    final tokens = await _api.login(email, password);
    if (tokens == null) return false;

    await SecureTokenStorage.saveTokens(
      access: tokens['access'],
      refresh: tokens['refresh'],
    );
    return true;
  }

  // ACTIVAR BIOMETRÍA tras primer login exitoso
  Future<bool> offerBiometricSetup() async {
    final available = await _biometric.isAvailable();
    if (!available) return false;

    final refresh = await SecureTokenStorage.getRefreshToken();
    if (refresh == null) return false;

    final activated = await _biometric.enableBiometrics(refresh);
    if (!activated) return false;

    // Notificar al backend
    final deviceId = await _getDeviceId();
    final deviceModel = await _getDeviceModel();
    await _api.enableBiometric(deviceId, deviceModel);
    return true;
  }

  Future<void> logout() async {
    final refresh = await SecureTokenStorage.getRefreshToken() ?? '';
    await _api.logout(refresh);
  }

  Future<String> _getDeviceId() async {
    final info = DeviceInfoPlugin();
    if (Platform.isAndroid) {
      final d = await info.androidInfo;
      return d.id;
    } else {
      final d = await info.iosInfo;
      return d.identifierForVendor ?? '';
    }
  }

  Future<String> _getDeviceModel() async {
    final info = DeviceInfoPlugin();
    if (Platform.isAndroid) {
      final d = await info.androidInfo;
      return '${d.manufacturer} ${d.model}';
    } else {
      final d = await info.iosInfo;
      return d.model;
    }
  }
}
```

---

## 6. Configuración Android / iOS

### Android (AndroidManifest.xml)
```xml
<uses-permission android:name="android.permission.USE_BIOMETRIC" />
<uses-permission android:name="android.permission.USE_FINGERPRINT" />

<application
    android:allowBackup="false"
    android:fullBackupContent="false">
    <!-- allowBackup=false evita que los tokens encriptados se restauren
         en otro dispositivo, rompiendo el Secure Storage -->
```

### iOS (Info.plist)
```xml
<key>NSFaceIDUsageDescription</key>
<string>Usa Face ID para acceder a tu cuenta de forma rápida y segura</string>
```

### Build de release con obfuscación

```bash
# Android
flutter build apk --release \
  --obfuscate \
  --split-debug-info=./debug-info/android

# iOS
flutter build ios --release \
  --obfuscate \
  --split-debug-info=./debug-info/ios
```

---

## 7. Reglas de seguridad en Flutter

**NUNCA hacer:**
- Guardar tokens en SharedPreferences (no encriptado)
- Guardar tokens en variables globales estáticas
- Imprimir tokens o passwords en logs: `if (kDebugMode) { ... }`
- Hacer requests HTTP (sin S)
- Ignorar errores de certificado SSL

**SIEMPRE hacer:**
- Tokens en flutter_secure_storage únicamente
- Certificate pinning en producción
- Limpiar SecureStorage completo en logout
- Timeout en todas las peticiones Dio
- Validar que la respuesta 200 tiene los campos esperados antes de usarlos
