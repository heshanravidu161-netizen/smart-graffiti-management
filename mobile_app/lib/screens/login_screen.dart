import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'home_screen.dart';
import 'sign_up_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();

  bool _isLoading = false;
  bool _hidePassword = true;

  static const Color purple = Color(0xFFA855F7);

  bool _validateLogin() {
    final email = _emailController.text.trim();
    final password = _passwordController.text;

    if (email.isEmpty || password.isEmpty) {
      _showMessage(
        'Please enter your email and password.',
        Colors.red,
      );
      return false;
    }

    if (!email.contains('@') || !email.contains('.')) {
      _showMessage(
        'Please enter a valid email address.',
        Colors.red,
      );
      return false;
    }

    return true;
  }

  Future<void> _login() async {
    if (!_validateLogin()) return;

    setState(() {
      _isLoading = true;
    });

    try {
      await Supabase.instance.client.auth.signInWithPassword(
        email: _emailController.text.trim(),
        password: _passwordController.text,
      );

      if (!mounted) return;

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => const HomeScreen(),
        ),
      );
    } on AuthException catch (error) {
      if (!mounted) return;
      _showMessage(error.message, Colors.red);
    } catch (error) {
      if (!mounted) return;
      _showMessage(
        'Login failed. Please try again.',
        Colors.red,
      );
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _forgotPassword() async {
    final email = _emailController.text.trim();

    if (email.isEmpty || !email.contains('@') || !email.contains('.')) {
      _showMessage(
        'Enter your email address first.',
        Colors.red,
      );
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      await Supabase.instance.client.auth.resetPasswordForEmail(
        email,
      );

      if (!mounted) return;

      _showMessage(
        'Password reset email sent. Check your inbox.',
        Colors.green,
      );
    } on AuthException catch (error) {
      if (!mounted) return;
      _showMessage(error.message, Colors.red);
    } catch (error) {
      if (!mounted) return;
      _showMessage(
        'Could not send the password reset email.',
        Colors.red,
      );
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  void _openSignUpScreen() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => const SignUpScreen(),
      ),
    );
  }

  void _showMessage(String message, Color colour) {
    ScaffoldMessenger.of(context).hideCurrentSnackBar();

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: colour,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF050505),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 26, vertical: 32),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Container(
                      width: 54,
                      height: 54,
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [
                            Color(0xFFFF8FCB),
                            purple,
                            Color(0xFF38BDF8)
                          ],
                        ),
                        borderRadius: BorderRadius.circular(17),
                      ),
                      child: const Icon(
                        Icons.remove_red_eye_rounded,
                        color: Colors.white,
                        size: 29,
                      ),
                    ),
                  ),
                  const SizedBox(height: 28),
                  const Text(
                    'Welcome back',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 30,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Sign in to continue to UrbanEyes.',
                    style: TextStyle(color: Color(0xFF8E8E95), fontSize: 14),
                  ),
                  const SizedBox(height: 34),
                  _LoginTextField(
                    controller: _emailController,
                    label: 'Email address',
                    icon: Icons.email_outlined,
                    keyboardType: TextInputType.emailAddress,
                  ),
                  const SizedBox(height: 14),
                  _LoginTextField(
                    controller: _passwordController,
                    label: 'Password',
                    icon: Icons.lock_outline_rounded,
                    obscureText: _hidePassword,
                    suffixIcon: IconButton(
                      onPressed: () {
                        setState(() {
                          _hidePassword = !_hidePassword;
                        });
                      },
                      icon: Icon(
                        _hidePassword
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined,
                        color: const Color(0xFF8E8E95),
                      ),
                    ),
                    onSubmitted: (_) {
                      if (!_isLoading) _login();
                    },
                  ),
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: _isLoading ? null : _forgotPassword,
                      child: const Text(
                        'Forgot password?',
                        style: TextStyle(color: purple, fontSize: 13),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  _GradientButton(
                    text: 'Sign in',
                    isLoading: _isLoading,
                    onPressed: _login,
                  ),
                  const SizedBox(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Text(
                        "Don't have an account?",
                        style:
                            TextStyle(color: Color(0xFF8E8E95), fontSize: 13),
                      ),
                      TextButton(
                        onPressed: _isLoading ? null : _openSignUpScreen,
                        child: const Text(
                          'Create account',
                          style: TextStyle(
                            color: purple,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _LoginTextField extends StatelessWidget {
  final TextEditingController controller;
  final String label;
  final IconData icon;
  final bool obscureText;
  final Widget? suffixIcon;
  final TextInputType? keyboardType;
  final ValueChanged<String>? onSubmitted;

  const _LoginTextField({
    required this.controller,
    required this.label,
    required this.icon,
    this.obscureText = false,
    this.suffixIcon,
    this.keyboardType,
    this.onSubmitted,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF121212),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white12),
      ),
      child: TextField(
        controller: controller,
        obscureText: obscureText,
        keyboardType: keyboardType,
        onSubmitted: onSubmitted,
        autocorrect: false,
        textInputAction:
            obscureText ? TextInputAction.done : TextInputAction.next,
        style: const TextStyle(color: Colors.white),
        decoration: InputDecoration(
          labelText: label,
          labelStyle: const TextStyle(color: Color(0xFF8E8E95)),
          prefixIcon: Icon(icon, color: const Color(0xFFA855F7)),
          suffixIcon: suffixIcon,
          filled: true,
          fillColor: const Color(0xFF121212),
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 18, vertical: 17),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: BorderSide.none,
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: BorderSide.none,
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: const BorderSide(
              color: Color(0xFFA855F7),
              width: 1.5,
            ),
          ),
        ),
      ),
    );
  }
}

class _GradientButton extends StatelessWidget {
  final String text;
  final bool isLoading;
  final VoidCallback onPressed;

  const _GradientButton({
    required this.text,
    required this.isLoading,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      height: 52,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [
            Color(0xFFA129F2),
            Color(0xFF3D00D9),
          ],
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF6C20E8).withValues(alpha: 0.35),
            blurRadius: 14,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: ElevatedButton(
        onPressed: isLoading ? null : onPressed,
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.transparent,
          disabledBackgroundColor: Colors.transparent,
          shadowColor: Colors.transparent,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
        ),
        child: isLoading
            ? const SizedBox(
                width: 23,
                height: 23,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.white,
                ),
              )
            : Text(
                text,
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                ),
              ),
      ),
    );
  }
}
