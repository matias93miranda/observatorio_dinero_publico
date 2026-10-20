# Certificados intermedios

`www.mecon.gob.ar` (Boletín Fiscal de la ONP) no envía el certificado intermedio en el handshake TLS
(verificado el 2026-10-19: `openssl s_client` → "unable to get local issuer certificate").
Navegadores lo completan solos; Python no. En lugar de desactivar la verificación, se agrega el
intermedio que el propio certificado del servidor declara en su extensión AIA:

| Archivo | Origen (AIA del servidor) | SHA-256 del certificado |
|---|---|---|
| `sectigo_public_server_authentication_ca_dv_r36.pem` | http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt | `8C:54:C3:34:B6:6B:A4:E4:26:77:2A:F4:A3:F9:13:6C:19:A1:AE:C7:29:FD:B2:8C:53:5C:07:A5:A4:EF:22:E0` |

Emisor: Sectigo Public Server Authentication Root R46 (raíz presente en los almacenes del sistema).
Vence el 2036-03-21. Solo se usa para los datasets que lo declaran (`DatasetDef.ca_extra`); el resto
usa el almacén del sistema sin cambios.
