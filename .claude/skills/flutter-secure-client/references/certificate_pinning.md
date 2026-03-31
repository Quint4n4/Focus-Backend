# Certificate Pinning Avanzado — Referencia Completa

## ¿Qué es y por qué es crítico?

Certificate Pinning asegura que Flutter solo se comunique con TU servidor.
Sin pinning, un atacante con acceso a la red del usuario puede instalar un
certificado propio y leer todo el tráfico HTTPS (ataque MITM).

## Método 1: Pinning con SHA-256 fingerprint (recomendado)

```dart
// Obtener el fingerprint de tu certificado:
// openssl s_client -connect api.tudominio.com:443 | openssl x509 -pubkey -noout | openssl pkey -pubin -outform der | openssl dgst -sha256 -binary | base64

import 'dart:io';
import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:dio/io.dart';

class SecureDioFactory {
  // SHA-256 del certificado público de tu servidor
  static const _expectedFingerprint =
      'ABC123...tu-fingerprint-en-base64-aqui...XYZ';

  static Dio create() {
    final dio = Dio(BaseOptions(baseUrl: 'https://api.tudominio.com/api/v1/'));

    (dio.httpClientAdapter as IOHttpClientAdapter).createHttpClient = () {
      final client = HttpClient();
      client.badCertificateCallback = _validateCertificate;
      return client;
    };

    return dio;
  }

  static bool _validateCertificate(X509Certificate cert, String host, int port) {
    if (host != 'api.tudominio.com') return false;

    // Calcular SHA-256 del certificado recibido
    final fingerprint = base64.encode(
      sha256.convert(cert.der).bytes,
    );

    // Comparar con el esperado
    return fingerprint == _expectedFingerprint;
  }
}
```

## Método 2: Pinning con archivo .pem embebido

```dart
// Poner el certificado en: assets/certificates/api.pem
// Declararlo en pubspec.yaml:
// flutter:
//   assets:
//     - assets/certificates/api.pem

import 'dart:io';
import 'package:flutter/services.dart';

Future<Dio> createSecureDio() async {
  final certData = await rootBundle.load('assets/certificates/api.pem');
  final certBytes = certData.buffer.asUint8List();

  final dio = Dio();
  (dio.httpClientAdapter as IOHttpClientAdapter).createHttpClient = () {
    final sc = SecurityContext(withTrustedRoots: false);
    sc.setTrustedCertificatesBytes(certBytes);
    final client = HttpClient(context: sc);
    client.badCertificateCallback = (cert, host, port) => false;
    return client;
  };

  return dio;
}
```

## Método 3: flutter_secure (paquete con pinning integrado)

```yaml
# pubspec.yaml
dependencies:
  flutter_secure: ^1.0.0
```

```dart
import 'package:flutter_secure/flutter_secure.dart';

// Con certificado PEM como string
final client1 = SSLPinningHttpClient([pemCertificateString]);

// Con Dio
Dio dio = Dio()
  ..interceptors.add(SSLPinningInterceptor([pemCertificateString]));
```

## Obtener el certificado de tu servidor

```bash
# Descargar el certificado en formato PEM
openssl s_client -connect api.tudominio.com:443 -showcerts </dev/null 2>/dev/null \
  | openssl x509 -outform PEM > assets/certificates/api.pem

# Obtener el SHA-256 fingerprint para el Método 1
openssl s_client -connect api.tudominio.com:443 </dev/null 2>/dev/null \
  | openssl x509 -pubkey -noout \
  | openssl pkey -pubin -outform der \
  | openssl dgst -sha256 -binary \
  | base64
```

## Manejo de error de pinning

```dart
try {
  final response = await dio.get('/api/data/');
} on DioException catch (e) {
  if (e.error is HandshakeException || e.error is TlsException) {
    // Certificate pinning falló — posible ataque MITM
    // NO continuar — mostrar error y cerrar sesión
    await SecureStorageService.clearAll();
    _navigateToLogin();
    _showSecurityAlert();
  }
}

void _showSecurityAlert() {
  showDialog(
    context: context,
    barrierDismissible: false,
    builder: (_) => AlertDialog(
      title: const Text('Alerta de seguridad'),
      content: const Text(
        'Se detectó una conexión insegura. '
        'Por tu seguridad, la sesión fue cerrada.'
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Entendido'),
        ),
      ],
    ),
  );
}
```

## Renovar el certificado (proceso obligatorio)

Los certificados TLS expiran (generalmente cada 90 días con Let's Encrypt,
1-2 años con certificados pagados). Cuando el certificado del servidor
renueva, el pinning fallará para usuarios con la app antigua.

**Estrategia recomendada: pinning de clave pública en lugar de certificado**

La clave pública NO cambia cuando renuevas el certificado con el mismo par
de claves, lo que evita el problema de renovación.

```bash
# Obtener fingerprint de la CLAVE PÚBLICA (no del certificado)
# Esta no cambia al renovar el certificado
openssl s_client -connect api.tudominio.com:443 </dev/null 2>/dev/null \
  | openssl x509 -pubkey -noout \
  | openssl pkey -pubin -outform der \
  | openssl dgst -sha256 -binary \
  | base64
```
