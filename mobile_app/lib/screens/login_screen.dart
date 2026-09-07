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
  bool _rememberMe = false;

  static const Color purple = Color(0xFF6C20E8);
  static const Color darkPurple = Color(0xFF3D00D9);

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
      backgroundColor: const Color(0xFFF4F3FA),
      body: Stack(
        children: [
          const Positioned.fill(
            child: ColoredBox(
              color: Color(0xFFF4F3FA),
            ),
          ),
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: ClipPath(
              clipper: _TopWaveClipper(),
              child: Container(
                height: 230,
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      darkPurple,
                      Color(0xFF9B20F5),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
              ),
            ),
          ),
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: ClipPath(
              clipper: _BottomWaveClipper(),
              child: Container(
                height: 180,
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      Color(0xFF9B20F5),
                      darkPurple,
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
              ),
            ),
          ),
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(
                  horizontal: 30,
                  vertical: 25,
                ),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 430),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        width: 82,
                        height: 82,
                        decoration: BoxDecoration(
                          color: Colors.white,
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.18),
                              blurRadius: 18,
                              offset: const Offset(0, 7),
                            ),
                          ],
                        ),
                        child: const Icon(
                          Icons.remove_red_eye_rounded,
                          color: purple,
                          size: 50,
                        ),
                      ),
                      const SizedBox(height: 24),
                      const Text(
                        'Welcome Back!',
                        style: TextStyle(
                          color: Color(0xFF171717),
                          fontSize: 34,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Sign in to your UrbanEyes account',
                        style: TextStyle(
                          color: Color(0xFF777777),
                          fontSize: 15,
                        ),
                      ),
                      const SizedBox(height: 38),
                      _LoginTextField(
                        controller: _emailController,
                        label: 'E-mail',
                        icon: Icons.email_rounded,
                        keyboardType: TextInputType.emailAddress,
                      ),
                      const SizedBox(height: 20),
                      _LoginTextField(
                        controller: _passwordController,
                        label: 'Password',
                        icon: Icons.lock_rounded,
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
                            color: purple,
                          ),
                        ),
                        onSubmitted: (_) {
                          if (!_isLoading) {
                            _login();
                          }
                        },
                      ),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          SizedBox(
                            width: 24,
                            height: 24,
                            child: Checkbox(
                              value: _rememberMe,
                              activeColor: purple,
                              side: const BorderSide(color: purple),
                              onChanged: (value) {
                                setState(() {
                                  _rememberMe = value ?? false;
                                });
                              },
                            ),
                          ),
                          const SizedBox(width: 7),
                          const Text(
                            'Remember me',
                            style: TextStyle(
                              color: Color(0xFF777777),
                              fontSize: 12,
                            ),
                          ),
                          const Spacer(),
                          TextButton(
                            onPressed: _isLoading ? null : _forgotPassword,
                            child: const Text(
                              'Forgot password?',
                              style: TextStyle(
                                color: purple,
                                fontSize: 12,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 15),
                      _GradientButton(
                        text: 'SIGN IN',
                        isLoading: _isLoading,
                        onPressed: _login,
                      ),
                      const SizedBox(height: 18),
                      const Text(
                        "Don't have an account?",
                        style: TextStyle(
                          color: Color(0xFF777777),
                          fontSize: 13,
                        ),
                      ),
                      const SizedBox(height: 10),
                      SizedBox(
                        width: double.infinity,
                        height: 52,
                        child: OutlinedButton.icon(
                          onPressed: _isLoading ? null : _openSignUpScreen,
                          icon: const Icon(Icons.person_add_alt_1),
                          label: const Text(
                            'CREATE NEW ACCOUNT',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: purple,
                            backgroundColor: Colors.white,
                            side: const BorderSide(
                              color: purple,
                              width: 1.5,
                            ),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(26),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 100),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
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
        color: Colors.white,
        borderRadius: BorderRadius.circular(30),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF6C20E8).withValues(alpha: 0.17),
            blurRadius: 18,
            offset: const Offset(0, 7),
          ),
        ],
      ),
      child: TextField(
        controller: controller,
        obscureText: obscureText,
        keyboardType: keyboardType,
        onSubmitted: onSubmitted,
        autocorrect: false,
        textInputAction:
            obscureText ? TextInputAction.done : TextInputAction.next,
        style: const TextStyle(color: Color(0xFF222222)),
        decoration: InputDecoration(
          labelText: label,
          labelStyle: const TextStyle(color: Color(0xFF888888)),
          prefixIcon: Icon(icon, color: const Color(0xFF6C20E8)),
          suffixIcon: suffixIcon,
          filled: true,
          fillColor: Colors.white,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 20,
            vertical: 18,
          ),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(30),
            borderSide: BorderSide.none,
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(30),
            borderSide: BorderSide.none,
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(30),
            borderSide: const BorderSide(
              color: Color(0xFF6C20E8),
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
      height: 54,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [
            Color(0xFFA129F2),
            Color(0xFF3D00D9),
          ],
        ),
        borderRadius: BorderRadius.circular(27),
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
            borderRadius: BorderRadius.circular(27),
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
                  fontWeight: FontWeight.bold,
                ),
              ),
      ),
    );
  }
}

class _TopWaveClipper extends CustomClipper<Path> {
  @override
  Path getClip(Size size) {
    final path = Path();

    path.lineTo(0, 0);
    path.lineTo(size.width, 0);
    path.lineTo(size.width, size.height * 0.57);

    path.cubicTo(
      size.width * 0.82,
      size.height * 0.80,
      size.width * 0.68,
      size.height * 0.48,
      size.width * 0.52,
      size.height * 0.69,
    );

    path.cubicTo(
      size.width * 0.35,
      size.height * 0.90,
      size.width * 0.23,
      size.height * 0.42,
      0,
      size.height * 0.65,
    );

    path.close();
    return path;
  }

  @override
  bool shouldReclip(CustomClipper<Path> oldClipper) => false;
}

class _BottomWaveClipper extends CustomClipper<Path> {
  @override
  Path getClip(Size size) {
    final path = Path();

    path.moveTo(0, size.height * 0.42);

    path.cubicTo(
      size.width * 0.20,
      size.height * 0.15,
      size.width * 0.35,
      size.height * 0.70,
      size.width * 0.52,
      size.height * 0.38,
    );

    path.cubicTo(
      size.width * 0.70,
      size.height * 0.08,
      size.width * 0.84,
      size.height * 0.62,
      size.width,
      size.height * 0.30,
    );

    path.lineTo(size.width, size.height);
    path.lineTo(0, size.height);
    path.close();

    return path;
  }

  @override
  bool shouldReclip(CustomClipper<Path> oldClipper) => false;
}
