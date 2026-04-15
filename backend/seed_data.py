#!/usr/bin/env python3
"""
Seed database with example support articles
Run: python seed_data.py
"""
import asyncio
from database import AsyncSessionLocal, init_db
from services.articles import ArticleService


SEED_ARTICLES = [
    {
        "slug": "password-reset",
        "content": {
            "en": {
                "title": "How to Reset Your Password",
                "body": """How to Reset Your Password:

If you've forgotten your password or need to reset it for security reasons, follow these steps:

1. Go to the login page
2. Click "Forgot Password" below the login form
3. Enter your registered email address
4. Check your email for a password reset link
5. Click the link and create a new password

Password Requirements:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character (!@#$%^&*)

Important Notes:
- Password reset links expire after 24 hours
- If you don't receive the email, check your spam folder
- You can only request a password reset once every 15 minutes
- For security, previous passwords cannot be reused

If you're still having trouble, contact our support team for assistance."""
            },
            "es": {
                "title": "Cómo restablecer tu contraseña",
                "body": """Cómo restablecer tu contraseña:

Si has olvidado tu contraseña o necesitas restablecerla por razones de seguridad, sigue estos pasos:

1. Ve a la página de inicio de sesión
2. Haz clic en "¿Olvidaste tu contraseña?" debajo del formulario
3. Ingresa tu dirección de correo electrónico registrada
4. Revisa tu correo electrónico para encontrar el enlace de restablecimiento
5. Haz clic en el enlace y crea una nueva contraseña

Requisitos de la contraseña:
- Mínimo 8 caracteres
- Al menos una letra mayúscula
- Al menos una letra minúscula
- Al menos un número
- Al menos un carácter especial (!@#$%^&*)

Notas importantes:
- Los enlaces de restablecimiento expiran después de 24 horas
- Si no recibes el correo, revisa tu carpeta de spam"""
            },
            "fr": {
                "title": "Comment réinitialiser votre mot de passe",
                "body": """Comment réinitialiser votre mot de passe:

Si vous avez oublié votre mot de passe ou devez le réinitialiser pour des raisons de sécurité, suivez ces étapes:

1. Allez sur la page de connexion
2. Cliquez sur "Mot de passe oublié" sous le formulaire
3. Entrez votre adresse e-mail enregistrée
4. Vérifiez votre e-mail pour le lien de réinitialisation
5. Cliquez sur le lien et créez un nouveau mot de passe

Exigences du mot de passe:
- Minimum 8 caractères
- Au moins une lettre majuscule
- Au moins une lettre minuscule
- Au moins un chiffre
- Au moins un caractère spécial (!@#$%^&*)"""
            }
        }
    },
    {
        "slug": "getting-started",
        "content": {
            "en": {
                "title": "Getting Started Guide",
                "body": """Getting Started Guide:

Welcome! This guide will help you get up and running quickly.

Step 1: Create Your Account
- Visit our website and click "Sign Up"
- Enter your email address and create a password
- Verify your email by clicking the confirmation link

Step 2: Complete Your Profile
- Add your name and profile picture
- Set your notification preferences
- Choose your language and timezone

Step 3: Explore the Dashboard
- The dashboard shows your recent activity
- Use the sidebar to navigate between sections
- Check the notifications bell for updates

Step 4: Key Features
- Search: Find content quickly using the search bar
- Settings: Customize your experience in preferences
- Help: Access support articles anytime from the help menu

Getting Help:
- Browse our knowledge base for answers
- Use the chat widget for quick questions
- Contact support for complex issues

Tips for Success:
- Enable two-factor authentication for better security
- Bookmark frequently used pages
- Check back regularly for new features and updates"""
            },
            "es": {
                "title": "Guía de inicio rápido",
                "body": """Guía de inicio rápido:

¡Bienvenido! Esta guía te ayudará a comenzar rápidamente.

Paso 1: Crea tu cuenta
- Visita nuestro sitio web y haz clic en "Registrarse"
- Ingresa tu dirección de correo electrónico y crea una contraseña
- Verifica tu correo haciendo clic en el enlace de confirmación

Paso 2: Completa tu perfil
- Agrega tu nombre y foto de perfil
- Configura tus preferencias de notificación
- Elige tu idioma y zona horaria

Paso 3: Explora el panel de control
- El panel muestra tu actividad reciente
- Usa la barra lateral para navegar entre secciones
- Revisa la campana de notificaciones para actualizaciones"""
            },
            "fr": {
                "title": "Guide de démarrage",
                "body": """Guide de démarrage:

Bienvenue! Ce guide vous aidera à démarrer rapidement.

Étape 1: Créez votre compte
- Visitez notre site Web et cliquez sur "S'inscrire"
- Entrez votre adresse e-mail et créez un mot de passe
- Vérifiez votre e-mail en cliquant sur le lien de confirmation

Étape 2: Complétez votre profil
- Ajoutez votre nom et photo de profil
- Définissez vos préférences de notification
- Choisissez votre langue et fuseau horaire

Étape 3: Explorez le tableau de bord
- Le tableau de bord affiche votre activité récente
- Utilisez la barre latérale pour naviguer entre les sections"""
            }
        }
    },
    {
        "slug": "billing-faq",
        "content": {
            "en": {
                "title": "Billing FAQ",
                "body": """Billing Frequently Asked Questions:

How do I update my payment method?
1. Go to Account Settings
2. Select "Billing & Payments"
3. Click "Update Payment Method"
4. Enter your new card details
5. Save changes

How do I view my billing history?
- Navigate to Account Settings > Billing
- Click "View Invoice History"
- Download invoices as PDF if needed

How do I cancel my subscription?
1. Go to Account Settings > Subscription
2. Click "Manage Subscription"
3. Select "Cancel Subscription"
4. Follow the prompts to confirm

Refund Policy:
- Refunds are available within 14 days of purchase
- To request a refund, contact support with your order number
- Refunds are processed within 5-7 business days
- Partial refunds may apply for used services

Common Billing Issues:
- Declined payment: Verify card details and available balance
- Double charge: Contact support; we'll investigate and refund if applicable
- Incorrect amount: Check your plan tier and any promotional discounts

Accepted Payment Methods:
- Credit cards (Visa, Mastercard, American Express)
- Debit cards
- PayPal
- Bank transfer (annual plans only)

Need more help? Contact our billing support team."""
            },
            "es": {
                "title": "Preguntas frecuentes sobre facturación",
                "body": """Preguntas frecuentes sobre facturación:

¿Cómo actualizo mi método de pago?
1. Ve a Configuración de la cuenta
2. Selecciona "Facturación y pagos"
3. Haz clic en "Actualizar método de pago"
4. Ingresa los detalles de tu nueva tarjeta
5. Guarda los cambios

¿Cómo veo mi historial de facturación?
- Navega a Configuración de cuenta > Facturación
- Haz clic en "Ver historial de facturas"
- Descarga facturas en PDF si es necesario

Política de reembolso:
- Los reembolsos están disponibles dentro de los 14 días posteriores a la compra
- Para solicitar un reembolso, contacta a soporte con tu número de orden
- Los reembolsos se procesan en 5-7 días hábiles"""
            },
            "fr": {
                "title": "FAQ Facturation",
                "body": """Questions fréquentes sur la facturation:

Comment mettre à jour mon mode de paiement?
1. Allez dans Paramètres du compte
2. Sélectionnez "Facturation et paiements"
3. Cliquez sur "Mettre à jour le mode de paiement"
4. Entrez les détails de votre nouvelle carte
5. Enregistrez les modifications

Comment consulter mon historique de facturation?
- Naviguez vers Paramètres du compte > Facturation
- Cliquez sur "Voir l'historique des factures"
- Téléchargez les factures en PDF si nécessaire

Politique de remboursement:
- Les remboursements sont disponibles dans les 14 jours suivant l'achat
- Pour demander un remboursement, contactez le support avec votre numéro de commande"""
            }
        }
    },
]


async def seed_database():
    """Seed the database with initial articles"""
    print("Initializing database...")
    await init_db()

    print("Seeding articles...")
    async with AsyncSessionLocal() as db:
        service = ArticleService(db)

        for article_data in SEED_ARTICLES:
            try:
                # Check if article already exists
                existing = await service.get_article(article_data["slug"])
                if existing:
                    print(f"- Skipping '{article_data['slug']}' (already exists)")
                    continue

                article = await service.create_article(
                    slug=article_data["slug"],
                    content=article_data["content"],
                    status="published",
                    created_by="seed_script"
                )
                title = article_data["content"]["en"]["title"]
                print(f"+ Created: {title}")
            except Exception as e:
                print(f"x Error creating '{article_data['slug']}': {e}")

    print("\nSeeding completed!")


if __name__ == "__main__":
    asyncio.run(seed_database())
