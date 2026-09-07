import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'home_screen.dart';

const Color _purple = Color(0xFF6C20E8);
const Color _darkPurple = Color(0xFF3D00D9);

class SignUpScreen extends StatefulWidget {
  const SignUpScreen({super.key});

  @override
  State<SignUpScreen> createState() => _SignUpScreenState();
}

class _SignUpScreenState extends State<SignUpScreen> {
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _phoneController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _confirmPasswordController =
      TextEditingController();

  bool _isLoading = false;
  bool _hidePassword = true;
  bool _hideConfirmPassword = true;

  // Password requirement checks.
  bool get _hasMinimumLength => _passwordController.text.length >= 8;

  bool get _hasUppercase => RegExp(r'[A-Z]').hasMatch(_passwordController.text);

  bool get _hasLowercase => RegExp(r'[a-z]').hasMatch(_passwordController.text);

  bool get _hasNumber => RegExp(r'[0-9]').hasMatch(_passwordController.text);

  bool get _hasSpecialCharacter =>
      RegExp(r'[!@#$%^&*(),.?":{}|<>]').hasMatch(_passwordController.text);

  bool get _isPasswordStrong =>
      _hasMinimumLength &&
      _hasUppercase &&
      _hasLowercase &&
      _hasNumber &&
      _hasSpecialCharacter;

  // Accepts 0412345678 or +61412345678.
  bool _isValidAustralianMobile(String phone) {
    final pattern = RegExp(r'^(?:04\d{8}|\+614\d{8})$');
    return pattern.hasMatch(phone);
  }

  // Converts 0412345678 into +61412345678.
  String _formatPhoneNumber(String phone) {
    if (phone.startsWith('04')) {
      return '+61${phone.substring(1)}';
    }

    return phone;
  }

  bool _validateForm() {
    final name = _nameController.text.trim();
    final email = _emailController.text.trim();
    final phone = _phoneController.text.trim();
    final password = _passwordController.text;
    final confirmPassword = _confirmPasswordController.text;

    if (name.isEmpty ||
        email.isEmpty ||
        phone.isEmpty ||
        password.isEmpty ||
        confirmPassword.isEmpty) {
      _showMessage(
        'Please complete every field.',
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

    if (!_isValidAustralianMobile(phone)) {
      _showMessage(
        'Enter an Australian mobile number such as 0412345678.',
        Colors.red,
      );
      return false;
    }

    if (!_isPasswordStrong) {
      _showMessage(
        'Your password does not meet all the requirements.',
        Colors.red,
      );
      return false;
    }

    if (password != confirmPassword) {
      _showMessage(
        'The passwords do not match.',
        Colors.red,
      );
      return false;
    }

    return true;
  }

  Future<void> _createAccount() async {
    if (!_validateForm()) return;

    final name = _nameController.text.trim();
    final email = _emailController.text.trim();
    final phone = _formatPhoneNumber(
      _phoneController.text.trim(),
    );
    final password = _passwordController.text;

    setState(() {
      _isLoading = true;
    });

    try {
      final response = await Supabase.instance.client.auth.signUp(
        email: email,
        password: password,
        data: {
          'display_name': name,
          'phone_number': phone,
          'country': 'Australia',
        },
      );

      if (!mounted) return;

      if (response.session != null) {
        Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(
            builder: (_) => const HomeScreen(),
          ),
          (route) => false,
        );
      } else {
        await showDialog<void>(
          context: context,
          barrierDismissible: false,
          builder: (dialogContext) {
            return AlertDialog(
              title: const Text('Account created'),
              content: const Text(
                'Please check your email and confirm your account. '
                'After confirming it, return to the login screen and sign in.',
              ),
              actions: [
                TextButton(
                  onPressed: () {
                    Navigator.pop(dialogContext);
                  },
                  child: const Text('OK'),
                ),
              ],
            );
          },
        );

        if (mounted) {
          Navigator.pop(context);
        }
      }
    } on AuthException catch (error) {
      if (!mounted) return;

      _showMessage(
        error.message,
        Colors.red,
      );
    } catch (error) {
      if (!mounted) return;

      _showMessage(
        'Could not create the account. Please try again.',
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

  // Displays one password guideline.
  Widget _passwordRequirement(
    String text,
    bool requirementMet,
  ) {
    final colour = requirementMet ? Colors.green : const Color(0xFF888888);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          Icon(
            requirementMet ? Icons.check_circle : Icons.radio_button_unchecked,
            color: colour,
            size: 18,
          ),
          const SizedBox(width: 8),
          Text(
            text,
            style: TextStyle(
              color: colour,
              fontSize: 12,
              fontWeight: requirementMet ? FontWeight.w600 : FontWeight.normal,
            ),
          ),
        ],
      ),
    );
  }

  InputDecoration _fieldDecoration({
    required String label,
    required IconData icon,
    String? hint,
    Widget? suffix,
  }) {
    return InputDecoration(
      labelText: label,
      hintText: hint,
      counterText: '',
      labelStyle: const TextStyle(
        color: Color(0xFF888888),
      ),
      hintStyle: const TextStyle(
        color: Color(0xFFAAAAAA),
      ),
      prefixIcon: Icon(
        icon,
        color: _purple,
      ),
      suffixIcon: suffix,
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
          color: _purple,
          width: 1.5,
        ),
      ),
    );
  }

  Widget _fieldContainer({
    required Widget child,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(30),
        boxShadow: [
          BoxShadow(
            color: _purple.withValues(alpha: 0.16),
            blurRadius: 17,
            offset: const Offset(0, 7),
          ),
        ],
      ),
      child: child,
    );
  }

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F3FA),
      body: Stack(
        children: [
          // Main light background.
          const Positioned.fill(
            child: ColoredBox(
              color: Color(0xFFF4F3FA),
            ),
          ),

          // Purple shape at the top.
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: ClipPath(
              clipper: _SignUpTopClipper(),
              child: Container(
                height: 210,
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      _darkPurple,
                      Color(0xFF9B20F5),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
              ),
            ),
          ),

          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(
                25,
                10,
                25,
                50,
              ),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(
                    maxWidth: 430,
                  ),
                  child: Column(
                    children: [
                      // Back button.
                      Align(
                        alignment: Alignment.centerLeft,
                        child: IconButton(
                          onPressed: _isLoading
                              ? null
                              : () {
                                  Navigator.pop(context);
                                },
                          icon: const Icon(
                            Icons.arrow_back_rounded,
                            color: Colors.white,
                          ),
                        ),
                      ),

                      const SizedBox(height: 15),

                      // Sign-up icon.
                      Container(
                        width: 76,
                        height: 76,
                        decoration: BoxDecoration(
                          color: Colors.white,
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(
                                alpha: 0.16,
                              ),
                              blurRadius: 15,
                              offset: const Offset(0, 6),
                            ),
                          ],
                        ),
                        child: const Icon(
                          Icons.person_add_alt_1_rounded,
                          color: _purple,
                          size: 43,
                        ),
                      ),

                      const SizedBox(height: 25),

                      const Text(
                        'Create Account',
                        style: TextStyle(
                          color: Color(0xFF171717),
                          fontSize: 32,
                          fontWeight: FontWeight.bold,
                        ),
                      ),

                      const SizedBox(height: 6),

                      const Text(
                        'Join UrbanEyes and help improve your community',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Color(0xFF777777),
                          fontSize: 14,
                        ),
                      ),

                      const SizedBox(height: 30),

                      // Full name field.
                      _fieldContainer(
                        child: TextField(
                          controller: _nameController,
                          keyboardType: TextInputType.name,
                          textInputAction: TextInputAction.next,
                          textCapitalization: TextCapitalization.words,
                          style: const TextStyle(
                            color: Color(0xFF222222),
                          ),
                          decoration: _fieldDecoration(
                            label: 'Full name',
                            icon: Icons.person_rounded,
                          ),
                        ),
                      ),

                      const SizedBox(height: 17),

                      // Email field.
                      _fieldContainer(
                        child: TextField(
                          controller: _emailController,
                          keyboardType: TextInputType.emailAddress,
                          textInputAction: TextInputAction.next,
                          autocorrect: false,
                          style: const TextStyle(
                            color: Color(0xFF222222),
                          ),
                          decoration: _fieldDecoration(
                            label: 'E-mail',
                            icon: Icons.email_rounded,
                          ),
                        ),
                      ),

                      const SizedBox(height: 17),

                      // Australian mobile-number field.
                      _fieldContainer(
                        child: TextField(
                          controller: _phoneController,
                          keyboardType: TextInputType.phone,
                          textInputAction: TextInputAction.next,
                          maxLength: 12,
                          inputFormatters: [
                            FilteringTextInputFormatter.allow(
                              RegExp(r'[0-9+]'),
                            ),
                          ],
                          style: const TextStyle(
                            color: Color(0xFF222222),
                          ),
                          decoration: _fieldDecoration(
                            label: 'Australian mobile number',
                            hint: '0412345678',
                            icon: Icons.phone_rounded,
                          ),
                        ),
                      ),

                      const SizedBox(height: 17),

                      // Password field.
                      _fieldContainer(
                        child: TextField(
                          controller: _passwordController,
                          obscureText: _hidePassword,
                          textInputAction: TextInputAction.next,
                          onChanged: (value) {
                            setState(() {});
                          },
                          style: const TextStyle(
                            color: Color(0xFF222222),
                          ),
                          decoration: _fieldDecoration(
                            label: 'Password',
                            icon: Icons.lock_rounded,
                            suffix: IconButton(
                              onPressed: () {
                                setState(() {
                                  _hidePassword = !_hidePassword;
                                });
                              },
                              icon: Icon(
                                _hidePassword
                                    ? Icons.visibility_outlined
                                    : Icons.visibility_off_outlined,
                                color: _purple,
                              ),
                            ),
                          ),
                        ),
                      ),

                      const SizedBox(height: 14),

                      // Live password guidelines.
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(18),
                          boxShadow: [
                            BoxShadow(
                              color: _purple.withValues(alpha: 0.10),
                              blurRadius: 12,
                              offset: const Offset(0, 5),
                            ),
                          ],
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Your password must contain:',
                              style: TextStyle(
                                color: Color(0xFF333333),
                                fontWeight: FontWeight.bold,
                                fontSize: 13,
                              ),
                            ),
                            const SizedBox(height: 10),
                            _passwordRequirement(
                              'At least 8 characters',
                              _hasMinimumLength,
                            ),
                            _passwordRequirement(
                              'One uppercase letter',
                              _hasUppercase,
                            ),
                            _passwordRequirement(
                              'One lowercase letter',
                              _hasLowercase,
                            ),
                            _passwordRequirement(
                              'One number',
                              _hasNumber,
                            ),
                            _passwordRequirement(
                              'One special character',
                              _hasSpecialCharacter,
                            ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 17),

                      // Confirm-password field.
                      _fieldContainer(
                        child: TextField(
                          controller: _confirmPasswordController,
                          obscureText: _hideConfirmPassword,
                          textInputAction: TextInputAction.done,
                          onSubmitted: (_) {
                            if (!_isLoading) {
                              _createAccount();
                            }
                          },
                          style: const TextStyle(
                            color: Color(0xFF222222),
                          ),
                          decoration: _fieldDecoration(
                            label: 'Confirm password',
                            icon: Icons.lock_reset_rounded,
                            suffix: IconButton(
                              onPressed: () {
                                setState(() {
                                  _hideConfirmPassword = !_hideConfirmPassword;
                                });
                              },
                              icon: Icon(
                                _hideConfirmPassword
                                    ? Icons.visibility_outlined
                                    : Icons.visibility_off_outlined,
                                color: _purple,
                              ),
                            ),
                          ),
                        ),
                      ),

                      const SizedBox(height: 28),

                      // Create-account button.
                      Container(
                        width: double.infinity,
                        height: 54,
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [
                              Color(0xFFA129F2),
                              _darkPurple,
                            ],
                          ),
                          borderRadius: BorderRadius.circular(27),
                          boxShadow: [
                            BoxShadow(
                              color: _purple.withValues(alpha: 0.35),
                              blurRadius: 14,
                              offset: const Offset(0, 6),
                            ),
                          ],
                        ),
                        child: ElevatedButton(
                          onPressed: _isLoading ? null : _createAccount,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.transparent,
                            disabledBackgroundColor: Colors.transparent,
                            shadowColor: Colors.transparent,
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(27),
                            ),
                          ),
                          child: _isLoading
                              ? const SizedBox(
                                  width: 23,
                                  height: 23,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.white,
                                  ),
                                )
                              : const Text(
                                  'CREATE ACCOUNT',
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 15,
                                  ),
                                ),
                        ),
                      ),

                      const SizedBox(height: 18),

                      // Return to login.
                      TextButton(
                        onPressed: _isLoading
                            ? null
                            : () {
                                Navigator.pop(context);
                              },
                        child: const Text(
                          'Already have an account? Sign in',
                          style: TextStyle(
                            color: _purple,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
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

// Creates the curved purple background.
class _SignUpTopClipper extends CustomClipper<Path> {
  @override
  Path getClip(Size size) {
    final path = Path();

    path.lineTo(0, 0);
    path.lineTo(size.width, 0);
    path.lineTo(size.width, size.height * 0.58);

    path.cubicTo(
      size.width * 0.75,
      size.height,
      size.width * 0.40,
      size.height * 0.45,
      0,
      size.height * 0.78,
    );

    path.close();
    return path;
  }

  @override
  bool shouldReclip(CustomClipper<Path> oldClipper) {
    return false;
  }
}
