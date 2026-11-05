# Despliegue siguiendo el diagrama ABP_Nube

La plantilla `deploy/aws-architecture.yml` implementa el diagrama web del documento **ABP_Nube.pdf**. No despliega la aplicación móvil.

## Recursos que crea

- VPC `10.0.0.0/16` con las seis subredes `/24` descritas en el informe, en dos zonas de disponibilidad.
- Internet Gateway, un NAT Gateway y las tablas de rutas pública, aplicación y datos.
- Gateway Endpoint privado de S3 asociado a la ruta de aplicación.
- Application Load Balancer público en las dos subredes públicas, con redirección HTTP→HTTPS.
- Grupo Auto Scaling con mínimo y deseado de 2 instancias EC2 (máximo 4), distribuidas en las subredes privadas de aplicación.
- RDS PostgreSQL Multi-AZ privado en las subredes de datos, cifrado y con backups automáticos.
- Bucket S3 privado con cifrado y versionado para imágenes de productos.
- Security Groups por capa, perfil IAM con SSM/S3 y acceso administrativo mediante Systems Manager.

La app se clona desde GitHub durante el arranque de cada instancia y se compila/ejecuta con Docker Compose. El ALB termina TLS mediante ACM. Las instancias leen secretos de SSM Parameter Store SecureString usando el rol IAM, no se abren puertos de base de datos, Django ni SSH al público.

## Costos importantes

Esta arquitectura **no es de bajo costo**: ALB, dos instancias EC2, NAT Gateway y RDS Multi-AZ facturan mientras están activos; además hay almacenamiento, transferencia y potencialmente IPv4 pública. La plantilla mantiene los recursos del diagrama, incluida alta disponibilidad. Revisa precios de `us-east-1` y créditos del Learner Lab antes de crear el stack. Si los créditos no alcanzan, no despliegues el stack completo; eliminar componentes cambia el diagrama.

El único NAT reduce el gasto respecto de uno por zona, pero crea un punto único de falla y salida para Stripe desde la segunda zona, tal como explica el ABP. RDS Multi-AZ y dos EC2 no sustituyen backups y monitoreo.

## Antes de lanzar

1. Confirma que la cuenta/laboratorio permite CloudFormation, VPC, NAT Gateway, ALB, EC2 Auto Scaling, RDS, S3, IAM, SSM y ACM. Algunas cuentas AWS Academy restringen servicios o tipos de instancias.
2. Los cambios de despliegue hechos en esta copia local deben estar en la rama GitHub que indique `GitRepository` y `GitBranch`: el UserData de las EC2 clona esa rama al arrancar. Publica los cambios en un repositorio al que AWS pueda acceder antes de crear el stack.
3. Selecciona la región `us-east-1` (el certificado ACM debe existir en esa misma región). Registra o elige un dominio y crea en ACM un certificado público validado para ese nombre.
4. En un equipo con AWS CLI configurado para la cuenta y región destino, ejecuta `bash deploy/aws/create-parameters.sh`. El script solicita la contraseña PostgreSQL y la clave Stripe, genera una clave Django, y los guarda como **SecureString** en Systems Manager Parameter Store:
   - `/tienda/prod/database-password`: contraseña PostgreSQL larga alfanumérica (sin `@`, `:`, `/` ni `%`, ya que se inserta en un `DATABASE_URL`).
   - `/tienda/prod/django-secret-key`: clave aleatoria larga; generar, por ejemplo, con `python3 -c 'import secrets; print(secrets.token_urlsafe(64))'`.
   - `/tienda/prod/stripe-secret-key`: clave de Stripe de prueba o producción, según corresponda.

   No guardes secretos en Git, parámetros normales, UserData escrito a mano o imágenes Docker. El stack espera que dichos parámetros ya existan. Verifica la región activa en AWS CLI antes de ejecutar el script.

## Crear el stack

En la consola AWS, abre **CloudFormation → Create stack → With new resources**, carga `deploy/aws-architecture.yml` y completa:

- `PublicDomainName`: el dominio del certificado ACM.
- `CertificateArn`: ARN del certificado en `us-east-1`.
- `DatabasePasswordParameterName`, `DjangoSecretParameterName`, `StripeSecretParameterName`: nombres de los parámetros SecureString anteriores.
- `InstanceType`: `t3.small` es el tamaño mínimo disponible en la plantilla; verifica que dé memoria suficiente al compilar Vite en ambas instancias.
- `GitBranch`: rama que quieres desplegar (por defecto `main`).
- `KeyPairName`: déjalo vacío si usarás Systems Manager Session Manager.

Marca la casilla de confirmación de capacidades IAM y crea el stack. Espera a que el grupo de Auto Scaling tenga dos instancias saludables en el Target Group. La primera compilación puede tardar varios minutos; los detalles están en `/var/log/tienda-bootstrap.log` (acceso por SSM).

Cuando CloudFormation entregue `LoadBalancerDnsName`, configura en tu proveedor DNS un registro `A/ALIAS` para `PublicDomainName` apuntando al ALB. ACM debe poder validar el dominio para que HTTPS quede operativo.

## Inicialización de la aplicación

La base arranca vacía. Tras verificar las instancias, usa Systems Manager Session Manager en una de ellas y crea el administrador:

```bash
cd /opt/tienda
docker compose -f docker-compose.ec2.yml exec backend python manage.py createsuperuser
```

El API se publica en `/api/v1/` y el panel en `/admin/`. La tienda usa PostgreSQL RDS; los archivos subidos mediante el campo de imagen del producto se guardan en S3 usando credenciales temporales del rol EC2. CORS está restringido; web y API comparten origen detrás del ALB.

## Migración y operación

- `db.sqlite3` e imágenes locales no se importan automáticamente. Migra los datos a PostgreSQL y copia imágenes a S3 antes de usar datos reales; ensaya y valida pedidos, stock, usuarios y relaciones en una base de prueba.
- El bucket está privado y las URL de imágenes se firman. No habilites acceso público al bucket.
- Eliminar el stack retiene el bucket y crea snapshot de RDS según las políticas de retención/protección. Para limpieza total, primero respalda, desactiva la protección de borrado de la instancia RDS y elimina manualmente el bucket retenido solo si estás seguro de que ya no necesitas sus datos.
- Configura alertas de presupuesto y CloudWatch. Supervisa consumo de créditos durante el laboratorio y elimina recursos cuando ya no los uses. Al eliminar el stack revisa también EIP/NAT, ALB, snapshots y volúmenes remanentes.

## Verificaciones y pendientes conocidas

En este entorno local pasaron las 56 pruebas backend, la compilación del frontend, `check --deploy` con variables productivas de validación y `npm audit --omit=dev` sin vulnerabilidades. No pude lanzar una construcción de Docker ni desplegar en AWS porque el daemon Docker no está disponible aquí y no tengo credenciales de tu cuenta.

La plantilla y los contenedores quedan preparados, pero el despliegue requiere los recursos/secretos de AWS descritos arriba, verificación de permisos/costos de tu cuenta y migración de datos. El historial Git del proyecto conserva una antigua clave Stripe de prueba: revócala en Stripe si sigue activa.
