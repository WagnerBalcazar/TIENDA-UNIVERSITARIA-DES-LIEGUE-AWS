from django.test import TestCase

# Create your tests here.
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date
from .models import PrivacyPolicy, Usuario, Producto, Rol, MetodoPago, Pedido, Venta, DetalleVenta

class ProductoApiTests(TestCase):
    """
    # Tests de Catálogo de Productos
    
    Cubre todos los casos de CRUD, filtrado, búsqueda y validaciones.
    """
    def setUp(self):
        self.client = APIClient()
        
        # Create test user for authenticated tests
        self.user = Usuario.objects.create_user(
            username='testuser@unl.edu.ec',
            email='testuser@unl.edu.ec',
            password='TestPassword123!',
            nombre_completo='Test User'
        )
        
        # Create test products
        self.p1 = Producto.objects.create(
            codigo="P001",
            nombre="Camiseta UNL",
            descripcion="Camiseta de algodón 100%",
            precio=15.50,
            stock=100,
            categoria="TEXTIL"
        )
        self.p2 = Producto.objects.create(
            codigo="P002",
            nombre="Gorra UNL",
            descripcion="Gorra ajustable negra",
            precio=8.00,
            stock=50,
            categoria="TEXTIL"
        )
        self.p3 = Producto.objects.create(
            codigo="P003",
            nombre="Bolsa Institucional",
            descripcion="Bolsa de lona con logo UNL",
            precio=12.00,
            stock=30,
            categoria="INSTITUCIONAL",
            is_activo=False  # Producto inactivo
        )
        
        self.list_url = reverse('producto-list')

    # ============= LIST & FILTER TESTS =============
    
    def test_list_products(self):
        """Test: GET /productos/ retorna lista paginada de productos activos"""
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        # Manejar respuesta paginada
        data = res.data.get('results', res.data) if isinstance(res.data, dict) else res.data
        nombres = [p['nombre'] for p in data]
        
        self.assertIn("Camiseta UNL", nombres)
        self.assertIn("Gorra UNL", nombres)
        # Producto inactivo no debe estar en la lista
        self.assertNotIn("Bolsa Institucional", nombres)
    
    def test_filter_by_categoria(self):
        """Test: GET /productos/?categoria=TEXTIL filtra por categoría"""
        res = self.client.get(self.list_url + '?categoria=TEXTIL')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        data = res.data.get('results', res.data) if isinstance(res.data, dict) else res.data
        # Solo productos TEXTIL activos
        self.assertEqual(len(data), 2)
        for producto in data:
            self.assertEqual(producto['categoria'], 'TEXTIL')
    
    def test_search_by_name(self):
        """Test: GET /productos/?search=Camiseta busca por nombre"""
        res = self.client.get(self.list_url + '?search=Camiseta')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        data = res.data.get('results', res.data) if isinstance(res.data, dict) else res.data
        # La búsqueda es case-insensitive y busca en nombre y descripción
        nombres = [p['nombre'] for p in data]
        self.assertIn('Camiseta UNL', nombres)
    
    def test_search_by_description(self):
        """Test: GET /productos/?search=algodón busca en descripción"""
        res = self.client.get(self.list_url + '?search=algodón')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        data = res.data.get('results', res.data) if isinstance(res.data, dict) else res.data
        # Busca en descripción: p1 contiene "algodón 100%"
        nombres = [p['nombre'] for p in data]
        self.assertIn('Camiseta UNL', nombres)
    
    def test_ordering_by_price_asc(self):
        """Test: GET /productos/?ordering=precio ordena por precio ascendente"""
        res = self.client.get(self.list_url + '?ordering=precio')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        data = res.data.get('results', res.data) if isinstance(res.data, dict) else res.data
        # Gorra (8.00) debe estar antes de Camiseta (15.50)
        self.assertEqual(data[0]['nombre'], 'Gorra UNL')
        self.assertEqual(data[1]['nombre'], 'Camiseta UNL')
    
    def test_ordering_by_price_desc(self):
        """Test: GET /productos/?ordering=-precio ordena por precio descendente"""
        res = self.client.get(self.list_url + '?ordering=-precio')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        data = res.data.get('results', res.data) if isinstance(res.data, dict) else res.data
        # Camiseta (15.50) debe estar primero
        self.assertEqual(data[0]['nombre'], 'Camiseta UNL')
        self.assertEqual(data[1]['nombre'], 'Gorra UNL')

    # ============= RETRIEVE TESTS =============
    
    def test_retrieve_product_detail(self):
        """Test: GET /productos/{id}/ retorna detalles del producto"""
        detail_url = reverse('producto-detail', kwargs={'pk': self.p1.id})
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['nombre'], "Camiseta UNL")
        self.assertEqual(res.data['codigo'], "P001")
        self.assertEqual(float(res.data['precio']), 15.50)
        self.assertEqual(res.data['stock'], 100)
    
    def test_retrieve_inactive_product_not_found(self):
        """Test: GET /productos/{id}/ retorna 404 para producto inactivo"""
        detail_url = reverse('producto-detail', kwargs={'pk': self.p3.id})
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_retrieve_nonexistent_product(self):
        """Test: GET /productos/999/ retorna 404"""
        detail_url = reverse('producto-detail', kwargs={'pk': 999})
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # ============= CREATE TESTS =============
    
    def test_create_product_authenticated(self):
        """Test: POST /productos/ crea producto (autenticado)"""
        self.client.force_authenticate(user=self.user)
        
        data = {
            "codigo": "P004",
            "nombre": "Sudadera UNL",
            "descripcion": "Sudadera gris oficial",
            "precio": 25.00,
            "stock": 40,
            "categoria": "TEXTIL"
        }
        
        res = self.client.post(self.list_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['nombre'], "Sudadera UNL")
        
        # Verify product in database
        self.assertTrue(Producto.objects.filter(codigo="P004").exists())
    
    def test_create_product_unauthenticated(self):
        """Test: POST /productos/ sin auth retorna 401"""
        data = {
            "codigo": "P004",
            "nombre": "Sudadera UNL",
            "descripcion": "Sudadera gris oficial",
            "precio": 25.00,
            "stock": 40
        }
        
        res = self.client.post(self.list_url, data, format='json')
        # IsAuthenticatedOrReadOnly devuelve 401 (no 403) cuando POST sin auth
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_product_invalid_price(self):
        """Test: POST con precio negativo retorna 400"""
        self.client.force_authenticate(user=self.user)
        
        data = {
            "codigo": "P004",
            "nombre": "Producto Inválido",
            "descripcion": "Test",
            "precio": -5.00,  # Invalid
            "stock": 10
        }
        
        res = self.client.post(self.list_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('precio', res.data)
    
    def test_create_product_invalid_stock(self):
        """Test: POST con stock negativo retorna 400"""
        self.client.force_authenticate(user=self.user)
        
        data = {
            "codigo": "P004",
            "nombre": "Producto Inválido",
            "descripcion": "Test",
            "precio": 10.00,
            "stock": -5  # Invalid
        }
        
        res = self.client.post(self.list_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('stock', res.data)
    
    def test_create_product_missing_required_field(self):
        """Test: POST sin campos requeridos retorna 400"""
        self.client.force_authenticate(user=self.user)
        
        data = {
            "codigo": "P004",
            # Missing: nombre (required)
            "descripcion": "Test",
            "precio": 10.00,
            "stock": 10
        }
        
        res = self.client.post(self.list_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('nombre', res.data)

    # ============= UPDATE TESTS =============
    
    def test_update_product_authenticated(self):
        """Test: PUT /productos/{id}/ actualiza producto (autenticado)"""
        self.client.force_authenticate(user=self.user)
        detail_url = reverse('producto-detail', kwargs={'pk': self.p1.id})
        
        # PUT requiere todos los campos requeridos del modelo
        data = {
            "codigo": "P001",
            "nombre": "Camiseta UNL - Actualizada",
            "descripcion": "Camiseta de algodón 100%",
            "precio": 18.00,
            "stock": 80,
            "categoria": "TEXTIL"
        }
        
        res = self.client.put(detail_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        # Verify in database
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.nombre, "Camiseta UNL - Actualizada")
        self.assertEqual(float(self.p1.precio), 18.00)
        self.assertEqual(self.p1.stock, 80)
    
    def test_update_product_unauthenticated(self):
        """Test: PUT sin auth retorna 401"""
        detail_url = reverse('producto-detail', kwargs={'pk': self.p1.id})
        
        data = {
            "precio": 20.00
        }
        
        res = self.client.put(detail_url, data, format='json')
        # IsAuthenticatedOrReadOnly devuelve 401 cuando PUT sin auth
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_update_product_nonexistent(self):
        """Test: PUT /productos/999/ retorna 404"""
        self.client.force_authenticate(user=self.user)
        detail_url = reverse('producto-detail', kwargs={'pk': 999})
        
        data = {"precio": 20.00}
        res = self.client.put(detail_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_update_product_invalid_price(self):
        """Test: PUT con precio inválido retorna 400"""
        self.client.force_authenticate(user=self.user)
        detail_url = reverse('producto-detail', kwargs={'pk': self.p1.id})
        
        data = {
            "nombre": "Camiseta UNL",
            "precio": -10.00
        }
        
        res = self.client.put(detail_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # ============= DELETE TESTS =============
    
    def test_delete_product_authenticated(self):
        """Test: DELETE /productos/{id}/ elimina producto (autenticado)"""
        self.client.force_authenticate(user=self.user)
        detail_url = reverse('producto-detail', kwargs={'pk': self.p1.id})
        
        res = self.client.delete(detail_url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        
        # Deletion is a soft delete so historical sales keep their product reference.
        self.p1.refresh_from_db()
        self.assertFalse(self.p1.is_activo)
    
    def test_delete_product_unauthenticated(self):
        """Test: DELETE sin auth retorna 401"""
        detail_url = reverse('producto-detail', kwargs={'pk': self.p1.id})
        
        res = self.client.delete(detail_url)
        # IsAuthenticatedOrReadOnly devuelve 401 cuando DELETE sin auth
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Verify product still exists
        self.assertTrue(Producto.objects.filter(pk=self.p1.id).exists())
    
    def test_delete_product_nonexistent(self):
        """Test: DELETE /productos/999/ retorna 404"""
        self.client.force_authenticate(user=self.user)
        detail_url = reverse('producto-detail', kwargs={'pk': 999})
        
        res = self.client.delete(detail_url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)



class RegistrationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.policy = PrivacyPolicy.objects.create(
            version="v1.0.0",
            content="Standard terms and conditions."
        )
        try:
            self.register_url = reverse('usuario-registro')
        except:
            self.register_url = '/api/v1/usuarios/registro/'

    def test_registration_success(self):
        data = {
            "nombre_completo": "John Doe",
            "email": "john.doe@unl.edu.ec",
            "password": "secure_password123",
            "identificacion": "1100000000",
            "telefono": "0999999999",
            "rol": Rol.CLIENTE,
            "is_universidad": True,
            "consentimiento_lopdp": True
        }
        res = self.client.post(self.register_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = Usuario.objects.get(email="john.doe@unl.edu.ec")
        self.assertTrue(user.consentimiento_lopdp)
        self.assertIsNotNone(user.consentimiento_timestamp)
        self.assertEqual(user.privacy_policy, self.policy)
        self.assertEqual(user.nombre_completo, "John Doe")
        self.assertEqual(user.identificacion, "1100000000")
        self.assertTrue(user.is_universidad)

    def test_registration_fails_without_consent(self):
        data = {
            "nombre_completo": "Jane Doe",
            "email": "jane.doe@unl.edu.ec",
            "password": "secure_password123",
            "telefono": "0999999999",
            "consentimiento_lopdp": False
        }
        res = self.client.post(self.register_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('consentimiento_lopdp', res.data)

    def test_registration_fails_invalid_email(self):
        data = {
            "nombre_completo": "Jane Doe",
            "email": "not-an-email",
            "password": "secure_password123",
            "telefono": "0999999999",
            "consentimiento_lopdp": True
        }
        res = self.client.post(self.register_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', res.data)
    
    def test_registration_fails_extra_fields(self):
        """Test: Registration rechaza campos extra (Data Minimization)"""
        data = {
            "nombre_completo": "John Doe",
            "email": "john.doe@unl.edu.ec",
            "password": "secure_password123",
            "telefono": "0999999999",
            "consentimiento_lopdp": True,
            "campo_extra": "dato no deseado"
        }
        res = self.client.post(self.register_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', res.data)


# ================= AUTHENTICATION TESTS =================

class AuthenticationTests(TestCase):
    """
    Tests para autenticación con JWT.
    
    Cubre: Login, Logout, Token Refresh, Perfil de Usuario
    """
    
    def setUp(self):
        """Configuración inicial para cada test"""
        self.client = APIClient()
        
        # Crear política de privacidad
        self.policy = PrivacyPolicy.objects.create(
            version="v1.0.0",
            content="Privacy policy content"
        )
        
        # Crear usuario de prueba
        self.usuario = Usuario.objects.create_user(
            username="juan.perez@unl.edu.ec",
            email="juan.perez@unl.edu.ec",
            password="TestPassword123!",
            nombre_completo="Juan Pérez García",
            identificacion="1103456789",
            telefono="0998765432",
            rol=Rol.CLIENTE,
            is_universidad=True,
            consentimiento_lopdp=True,
            privacy_policy=self.policy,
            is_active=True
        )
        
        # URLs de endpoints
        self.login_url = reverse('auth-login')
        self.logout_url = reverse('auth-logout')
        self.refresh_url = reverse('auth-refresh')
        self.profile_url = reverse('usuario-profile')
    
    # ================= LOGIN TESTS =================
    
    def test_login_success_with_valid_credentials(self):
        """Test: Login exitoso con credenciales válidas"""
        data = {
            "email": "juan.perez@unl.edu.ec",
            "password": "TestPassword123!"
        }
        res = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'success')
        self.assertIn('access_token', res.data)
        self.assertIn('refresh_token', res.data)
        self.assertEqual(res.data['user']['email'], "juan.perez@unl.edu.ec")
        self.assertEqual(res.data['user']['nombre_completo'], "Juan Pérez García")
    
    def test_login_fails_with_invalid_password(self):
        """Test: Login falla con contraseña incorrecta"""
        data = {
            "email": "juan.perez@unl.edu.ec",
            "password": "WrongPassword123!"
        }
        res = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['status'], 'error')
    
    def test_login_fails_with_nonexistent_email(self):
        """Test: Login falla con email inexistente"""
        data = {
            "email": "noexiste@unl.edu.ec",
            "password": "TestPassword123!"
        }
        res = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['status'], 'error')
    
    def test_login_fails_missing_email(self):
        """Test: Login falla sin email"""
        data = {
            "password": "TestPassword123!"
        }
        res = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_fails_missing_password(self):
        """Test: Login falla sin contraseña"""
        data = {
            "email": "juan.perez@unl.edu.ec"
        }
        res = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_fails_inactive_user(self):
        """Test: Login falla si usuario está inactivo"""
        # Desactivar usuario
        self.usuario.is_active = False
        self.usuario.save()
        
        data = {
            "email": "juan.perez@unl.edu.ec",
            "password": "TestPassword123!"
        }
        res = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
    
    # ================= TOKEN REFRESH TESTS =================
    
    def test_token_refresh_success_with_valid_refresh_token(self):
        """Test: Token refresh exitoso con refresh token válido"""
        # Primero login para obtener tokens
        login_data = {
            "email": "juan.perez@unl.edu.ec",
            "password": "TestPassword123!"
        }
        login_res = self.client.post(self.login_url, login_data, format='json')
        refresh_token = login_res.data['refresh_token']
        
        # Ahora refresh
        refresh_data = {
            "refresh": refresh_token
        }
        res = self.client.post(self.refresh_url, refresh_data, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data)
    
    def test_token_refresh_fails_invalid_token(self):
        """Test: Token refresh falla con token inválido"""
        refresh_data = {
            "refresh": "invalid.token.here"
        }
        res = self.client.post(self.refresh_url, refresh_data, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
    
    # ================= LOGOUT TESTS =================
    
    def test_logout_success(self):
        """Test: Logout exitoso"""
        # Primero login
        login_data = {
            "email": "juan.perez@unl.edu.ec",
            "password": "TestPassword123!"
        }
        login_res = self.client.post(self.login_url, login_data, format='json')
        refresh_token = login_res.data['refresh_token']
        
        # Ahora logout
        logout_data = {
            "refresh": refresh_token
        }
        res = self.client.post(self.logout_url, logout_data, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'success')
    
    def test_logout_fails_missing_refresh_token(self):
        """Test: Logout falla sin refresh token"""
        res = self.client.post(self.logout_url, {}, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
    
    # ================= PROFILE TESTS =================
    
    def test_get_profile_success_authenticated(self):
        """Test: Obtener perfil exitosamente cuando está autenticado"""
        # Login primero
        login_data = {
            "email": "juan.perez@unl.edu.ec",
            "password": "TestPassword123!"
        }
        login_res = self.client.post(self.login_url, login_data, format='json')
        access_token = login_res.data['access_token']
        
        # Obtener perfil con token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        res = self.client.get(self.profile_url)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['email'], "juan.perez@unl.edu.ec")
        self.assertEqual(res.data['nombre_completo'], "Juan Pérez García")
        self.assertEqual(res.data['identificacion'], "1103456789")
    
    def test_get_profile_fails_unauthenticated(self):
        """Test: Obtener perfil falla sin autenticación"""
        res = self.client.get(self.profile_url)
        
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_update_profile_success(self):
        """Test: Actualizar perfil exitosamente"""
        # Login primero
        login_data = {
            "email": "juan.perez@unl.edu.ec",
            "password": "TestPassword123!"
        }
        login_res = self.client.post(self.login_url, login_data, format='json')
        access_token = login_res.data['access_token']
        
        # Actualizar perfil
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        update_data = {
            "nombre_completo": "Juan Carlos Pérez García",
            "telefono": "0999888777"
        }
        res = self.client.put(self.profile_url, update_data, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'success')
        self.assertEqual(res.data['user']['nombre_completo'], "Juan Carlos Pérez García")
        self.assertEqual(res.data['user']['telefono'], "0999888777")
    
    def test_update_profile_cannot_change_email(self):
        """Test: Email no puede ser cambiado via actualización de perfil"""
        # Login primero
        login_data = {
            "email": "juan.perez@unl.edu.ec",
            "password": "TestPassword123!"
        }
        login_res = self.client.post(self.login_url, login_data, format='json')
        access_token = login_res.data['access_token']
        
        # Intentar cambiar email
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        update_data = {
            "email": "newemail@unl.edu.ec"
        }
        res = self.client.put(self.profile_url, update_data, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Email debe seguir siendo el mismo
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.email, "juan.perez@unl.edu.ec")
    
    def test_update_profile_invalid_nombre_too_short(self):
        """Test: Nombre demasiado corto es rechazado"""
        # Login primero
        login_data = {
            "email": "juan.perez@unl.edu.ec",
            "password": "TestPassword123!"
        }
        login_res = self.client.post(self.login_url, login_data, format='json')
        access_token = login_res.data['access_token']
        
        # Intentar actualizar con nombre muy corto
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        update_data = {
            "nombre_completo": "AB"
        }
        res = self.client.put(self.profile_url, update_data, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

class PrivacyPolicyApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.policy1 = PrivacyPolicy.objects.create(version="v1.0", content="Old")
        import time
        time.sleep(0.1)  # Asegurar que policy2 sea más reciente
        self.policy2 = PrivacyPolicy.objects.create(version="v2.0", content="New")
        try:
            self.policy_url = reverse('politica-privacidad')
        except:
            self.policy_url = '/api/v1/politica-privacidad/'

    def test_get_latest_policy(self):
        res = self.client.get(self.policy_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['version'], "v2.0")
        self.assertEqual(res.data['contenido'], "New")


class PedidoApiTests(TestCase):
    """
    # Tests de Sistema de Órdenes/Pedidos
    
    Cubre creación, listado, visualización de detalles, transiciones de estado
    y validación de stock.
    """
    
    def setUp(self):
        """Setup inicial con usuarios, productos y política de privacidad"""
        self.client = APIClient()
        
        # Crear política de privacidad
        self.policy = PrivacyPolicy.objects.create(
            version="v1.0.0",
            content="Privacy policy"
        )
        
        # Crear usuarios de prueba
        self.cliente = Usuario.objects.create_user(
            username='cliente@unl.edu.ec',
            email='cliente@unl.edu.ec',
            password='TestPassword123!',
            nombre_completo='Cliente Test',
            consentimiento_lopdp=True,
            privacy_policy=self.policy
        )
        
        self.admin = Usuario.objects.create_user(
            username='admin@unl.edu.ec',
            email='admin@unl.edu.ec',
            password='AdminPassword123!',
            nombre_completo='Admin Test',
            rol=Rol.ADMINISTRADOR,
            consentimiento_lopdp=True,
            privacy_policy=self.policy
        )
        
        # Crear productos de prueba
        self.p1 = Producto.objects.create(
            codigo="P001",
            nombre="Camiseta UNL",
            descripcion="Camiseta de algodón",
            precio=15.50,
            stock=20,
            categoria="TEXTIL",
            is_activo=True,
            aplica_impuesto=False
        )
        
        self.p2 = Producto.objects.create(
            codigo="P002",
            nombre="Gorra UNL",
            descripcion="Gorra negra",
            precio=8.00,
            stock=5,
            categoria="TEXTIL",
            is_activo=True,
            aplica_impuesto=False
        )
        
        self.p3_inactivo = Producto.objects.create(
            codigo="P003",
            nombre="Bolsa Antigua",
            descripcion="No disponible",
            precio=12.00,
            stock=10,
            categoria="ACCESORIOS",
            is_activo=False
        )
        
        self.list_url = reverse('pedido-list')
    
    # ============= CREATE TESTS =============
    
    def test_create_order_success(self):
        """Test: Crear orden exitosamente con stock válido"""
        self.client.force_authenticate(user=self.cliente)
        
        data = {
            "tipo_entrega": "TIENDA",
            "detalles": [
                {"producto_id": self.p1.id, "cantidad": 2}
            ]
        }
        
        res = self.client.post(self.list_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn('numero_pedido', res.data)
        self.assertEqual(res.data['estado'], 'RECIBIDO')
        self.assertEqual(res.data['tipo_entrega'], 'TIENDA')
        self.assertEqual(float(res.data['total']), 31.00)  # 15.50 * 2
        
        # Verificar stock reducido
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 18)  # 20 - 2
    
    def test_create_order_multiple_items(self):
        """Test: Crear orden con múltiples productos"""
        self.client.force_authenticate(user=self.cliente)
        
        data = {
            "tipo_entrega": "DOMICILIO",
            "detalles": [
                {"producto_id": self.p1.id, "cantidad": 2},
                {"producto_id": self.p2.id, "cantidad": 1}
            ]
        }
        
        res = self.client.post(self.list_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(res.data['detalles']), 2)
        # Total: (15.50 * 2) + (8.00 * 1) = 39.00
        self.assertEqual(float(res.data['total']), 39.00)
    
    def test_create_order_insufficient_stock(self):
        """Test: Crear orden con stock insuficiente retorna 400"""
        self.client.force_authenticate(user=self.cliente)
        
        data = {
            "tipo_entrega": "TIENDA",
            "detalles": [
                {"producto_id": self.p2.id, "cantidad": 10}  # Solo hay 5
            ]
        }
        
        res = self.client.post(self.list_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detalles', res.data)
        self.assertIn('Stock insuficiente', str(res.data['detalles']))
    
    def test_create_order_inactive_product(self):
        """Test: No se puede crear orden con producto inactivo"""
        self.client.force_authenticate(user=self.cliente)
        
        data = {
            "tipo_entrega": "TIENDA",
            "detalles": [
                {"producto_id": self.p3_inactivo.id, "cantidad": 1}
            ]
        }
        
        res = self.client.post(self.list_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detalles', res.data)
    
    def test_create_order_unauthenticated(self):
        """Test: POST sin auth retorna 401"""
        data = {
            "tipo_entrega": "TIENDA",
            "detalles": [
                {"producto_id": self.p1.id, "cantidad": 1}
            ]
        }
        
        res = self.client.post(self.list_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
    
    # ============= LIST TESTS =============
    
    def test_list_own_orders_customer(self):
        """Test: Cliente ve solo sus pedidos"""
        # Crear pedidos para diferentes usuarios
        from tienda.models import Pedido
        pedido1 = Pedido.objects.create(
            numero_pedido="P-20260527-001",
            cliente=self.cliente,
            estado='RECIBIDO',
            tipo_entrega='TIENDA',
            subtotal=15.50,
            impuesto=0.00,
            total=15.50
        )
        pedido2 = Pedido.objects.create(
            numero_pedido="P-20260527-002",
            cliente=self.admin,
            estado='RECIBIDO',
            tipo_entrega='TIENDA',
            subtotal=10.00,
            impuesto=0.00,
            total=10.00
        )
        
        self.client.force_authenticate(user=self.cliente)
        res = self.client.get(self.list_url)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Cliente solo ve sus 2 pedidos (1 creado en setup + 1 creado ahora)
        self.assertEqual(res.data['count'], 1)  # Solo el suyo
    
    def test_list_all_orders_admin(self):
        """Test: Admin ve todos los pedidos"""
        from tienda.models import Pedido
        pedido1 = Pedido.objects.create(
            numero_pedido="P-20260527-001",
            cliente=self.cliente,
            estado='RECIBIDO',
            tipo_entrega='TIENDA',
            subtotal=15.50,
            impuesto=0.00,
            total=15.50
        )
        pedido2 = Pedido.objects.create(
            numero_pedido="P-20260527-002",
            cliente=self.admin,
            estado='RECIBIDO',
            tipo_entrega='TIENDA',
            subtotal=10.00,
            impuesto=0.00,
            total=10.00
        )
        
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(self.list_url)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 2)  # Ve todos
    
    # ============= STATE TRANSITION TESTS =============
    
    def test_update_order_status_valid_transition(self):
        """Test: Transición válida RECIBIDO → PREPARACION"""
        from tienda.models import Pedido
        pedido = Pedido.objects.create(
            numero_pedido="P-20260527-001",
            cliente=self.cliente,
            estado='RECIBIDO',
            tipo_entrega='TIENDA',
            subtotal=15.50,
            impuesto=0.00,
            total=15.50
        )
        
        self.client.force_authenticate(user=self.admin)
        detail_url = reverse('pedido-detail', kwargs={'pk': pedido.id})
        
        data = {"estado": "PREPARACION"}
        res = self.client.put(detail_url, data, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['estado'], 'PREPARACION')
        
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'PREPARACION')
    
    def test_update_order_status_invalid_transition(self):
        """Test: Transición inválida retorna 400"""
        from tienda.models import Pedido
        pedido = Pedido.objects.create(
            numero_pedido="P-20260527-001",
            cliente=self.cliente,
            estado='ENTREGADO',
            tipo_entrega='TIENDA',
            subtotal=15.50,
            impuesto=0.00,
            total=15.50
        )
        
        self.client.force_authenticate(user=self.admin)
        detail_url = reverse('pedido-detail', kwargs={'pk': pedido.id})
        
        # Intentar ir de ENTREGADO a PREPARACION (inválido)
        data = {"estado": "PREPARACION"}
        res = self.client.put(detail_url, data, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Transición', str(res.data))
    
    def test_cancel_order_and_release_stock(self):
        """Test: Cancelar orden libera el stock"""
        from tienda.models import Pedido, Venta, DetalleVenta
        
        # Crear pedido con detalles
        pedido = Pedido.objects.create(
            numero_pedido="P-20260527-001",
            cliente=self.cliente,
            estado='RECIBIDO',
            tipo_entrega='TIENDA',
            subtotal=31.00,
            impuesto=0.00,
            total=31.00
        )
        
        # Crear venta y detalles
        venta = Venta.objects.create(
            pedido=pedido,
            cajero=self.admin,
            subtotal=31.00,
            metodo_pago='EFECTIVO'
        )
        
        DetalleVenta.objects.create(
            pedido=pedido,
            producto=self.p1,
            nombre_producto="Camiseta UNL",
            cantidad=2,
            precio_unitario=15.50,
            subtotal=31.00
        )
        
        # Reducir stock manualmente para simular compra
        self.p1.stock -= 2
        self.p1.save()
        self.assertEqual(self.p1.stock, 18)
        
        # Cancelar orden
        self.client.force_authenticate(user=self.admin)
        detail_url = reverse('pedido-detail', kwargs={'pk': pedido.id})
        
        data = {"estado": "CANCELADO"}
        res = self.client.put(detail_url, data, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['estado'], 'CANCELADO')
        
        # Verificar stock liberado
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 20)  # 18 + 2

    def test_order_number_uniqueness(self):
        """Test: Verificar que numero_pedido es único"""
        from tienda.models import Pedido
        
        self.client.force_authenticate(user=self.cliente)
        
        # Crear primer pedido
        data1 = {
            "tipo_entrega": "TIENDA",
            "detalles": [
                {"producto_id": self.p1.id, "cantidad": 1}
            ]
        }
        res1 = self.client.post(self.list_url, data1, format='json')
        numero1 = res1.data['numero_pedido']
        
        # Crear segundo pedido
        data2 = {
            "tipo_entrega": "TIENDA",
            "detalles": [
                {"producto_id": self.p2.id, "cantidad": 1}
            ]
        }
        res2 = self.client.post(self.list_url, data2, format='json')
        numero2 = res2.data['numero_pedido']
        
        # Verificar que son diferentes
        self.assertNotEqual(numero1, numero2)
        
        # Verificar que ambos existen en BD
        self.assertTrue(Pedido.objects.filter(numero_pedido=numero1).exists())
        self.assertTrue(Pedido.objects.filter(numero_pedido=numero2).exists())

    def test_admin_only_state_update(self):
        """Test: Solo administradores pueden cambiar estado"""
        from tienda.models import Pedido
        
        # Crear pedido como cliente
        self.client.force_authenticate(user=self.cliente)
        data = {
            "tipo_entrega": "TIENDA",
            "detalles": [
                {"producto_id": self.p1.id, "cantidad": 1}
            ]
        }
        res = self.client.post(self.list_url, data, format='json')
        pedido_id = res.data['id']
        
        # Cliente intenta cambiar estado (debe fallar)
        detail_url = reverse('pedido-detail', kwargs={'pk': pedido_id})
        update_data = {"estado": "PREPARACION"}
        res = self.client.put(detail_url, update_data, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        
        # Admin puede cambiar estado (debe funcionar)
        self.client.force_authenticate(user=self.admin)
        res = self.client.put(detail_url, update_data, format='json')
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['estado'], 'PREPARACION')

    def test_state_transition_sequence(self):
        """Test: Secuencia completa de transiciones de estado"""
        from tienda.models import Pedido
        
        # Crear pedido
        self.client.force_authenticate(user=self.cliente)
        data = {
            "tipo_entrega": "TIENDA",
            "detalles": [
                {"producto_id": self.p1.id, "cantidad": 1}
            ]
        }
        res = self.client.post(self.list_url, data, format='json')
        pedido_id = res.data['id']
        detail_url = reverse('pedido-detail', kwargs={'pk': pedido_id})
        
        # Autenticar como admin
        self.client.force_authenticate(user=self.admin)
        
        # Secuencia: RECIBIDO → PREPARACION
        res = self.client.put(detail_url, {"estado": "PREPARACION"}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['estado'], 'PREPARACION')
        
        # PREPARACION → LISTO
        res = self.client.put(detail_url, {"estado": "LISTO"}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['estado'], 'LISTO')
        
        # LISTO → ENTREGADO
        res = self.client.put(detail_url, {"estado": "ENTREGADO"}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['estado'], 'ENTREGADO')

    def test_order_cannot_be_deleted(self):
        """Test: No se puede borrar órdenes (solo transiciones de estado)"""
        from tienda.models import Pedido
        
        # Crear pedido
        self.client.force_authenticate(user=self.cliente)
        data = {
            "tipo_entrega": "TIENDA",
            "detalles": [
                {"producto_id": self.p1.id, "cantidad": 1}
            ]
        }
        res = self.client.post(self.list_url, data, format='json')
        pedido_id = res.data['id']
        
        # Intentar borrar como cliente
        detail_url = reverse('pedido-detail', kwargs={'pk': pedido_id})
        res = self.client.delete(detail_url)
        
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Intentar borrar como admin
        self.client.force_authenticate(user=self.admin)
        res = self.client.delete(detail_url)
        
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Verificar que la orden sigue existiendo
        self.assertTrue(Pedido.objects.filter(id=pedido_id).exists())

    def test_permission_denial_for_non_admins(self):
        """Test: Verificar que solo admins/bodeguero/cajero pueden actualizar estado"""
        from tienda.models import Usuario, Rol, Pedido
        
        # Crear pedido como cliente
        self.client.force_authenticate(user=self.cliente)
        data = {
            "tipo_entrega": "TIENDA",
            "detalles": [
                {"producto_id": self.p1.id, "cantidad": 1}
            ]
        }
        res = self.client.post(self.list_url, data, format='json')
        pedido_id = res.data['id']
        detail_url = reverse('pedido-detail', kwargs={'pk': pedido_id})
        
        # Cliente intenta cambiar estado (debe fallar - es su propio pedido pero no es bodeguero)
        update_data = {"estado": "PREPARACION"}
        res = self.client.put(detail_url, update_data, format='json')
        
        # El cliente no puede ver la acción de actualizar porque no es en la lista,
        # sino que debe fallar con 403
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

