import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:image_picker/image_picker.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../services/report_service.dart';
import 'map_picker_screen.dart';

class SubmitReportScreen extends StatefulWidget {
  const SubmitReportScreen({super.key});

  @override
  State<SubmitReportScreen> createState() => _SubmitReportScreenState();
}

class _SubmitReportScreenState extends State<SubmitReportScreen> {
  final ReportService _service = ReportService();

  final TextEditingController _notesController = TextEditingController();

  XFile? _capturedImage;
  double? _latitude;
  double? _longitude;

  bool _submitting = false;
  bool _isConfirmed = false;

  static const Color _purpleAccent = Color(0xFFA855F7);

  @override
  void dispose() {
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _pickImage() async {
    try {
      final picker = ImagePicker();

      final image = await picker.pickImage(
        source: ImageSource.camera,
        imageQuality: 85,
        maxWidth: 1920,
      );

      if (image != null && mounted) {
        setState(() {
          _capturedImage = image;
        });
      }
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Could not open the camera: $e',
          ),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  Future<void> _useCurrentLocation() async {
    try {
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();

      if (!serviceEnabled) {
        throw Exception(
          'Location services are disabled.',
        );
      }

      LocationPermission permission = await Geolocator.checkPermission();

      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }

      if (permission == LocationPermission.denied) {
        throw Exception(
          'Location permission was denied.',
        );
      }

      if (permission == LocationPermission.deniedForever) {
        throw Exception(
          'Location permission is permanently denied. '
          'Please enable it in your device settings.',
        );
      }

      final position = await Geolocator.getCurrentPosition();

      if (!mounted) return;

      setState(() {
        _latitude = position.latitude;
        _longitude = position.longitude;
      });
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Could not get location: $e',
          ),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  Future<void> _pickOnMap() async {
    final start = LatLng(
      _latitude ?? -31.9523,
      _longitude ?? 115.8613,
    );

    final result = await Navigator.push<LatLng>(
      context,
      MaterialPageRoute(
        builder: (_) => MapPickerScreen(
          initialLocation: start,
        ),
      ),
    );

    if (result != null && mounted) {
      setState(() {
        _latitude = result.latitude;
        _longitude = result.longitude;
      });
    }
  }

  bool get _canSubmit {
    return _capturedImage != null &&
        _latitude != null &&
        _longitude != null &&
        _isConfirmed;
  }

  Future<String> _uploadImage() async {
    if (_capturedImage == null) {
      throw Exception(
        'Please take a photo first.',
      );
    }

    final supabase = Supabase.instance.client;

    // Read the image as bytes.
    // This works on Flutter Web, Android and iOS.
    final Uint8List imageBytes = await _capturedImage!.readAsBytes();

    final originalName = _capturedImage!.name;
    final dotPosition = originalName.lastIndexOf('.');

    final extension = dotPosition >= 0
        ? originalName.substring(dotPosition + 1).toLowerCase()
        : 'jpg';

    final fileName =
        'report_${DateTime.now().millisecondsSinceEpoch}.$extension';

    final storagePath = 'reports/$fileName';

    // Upload the image to Supabase Storage.
    await supabase.storage.from('report-images').uploadBinary(
          storagePath,
          imageBytes,
          fileOptions: FileOptions(
            contentType: _capturedImage!.mimeType ?? 'image/jpeg',
            upsert: false,
          ),
        );

    // Get the public image URL.
    final publicUrl =
        supabase.storage.from('report-images').getPublicUrl(storagePath);

    return publicUrl;
  }

  Future<void> _submit() async {
    if (!_canSubmit || _submitting) return;

    setState(() {
      _submitting = true;
    });

    try {
      //

      final user = Supabase.instance.client.auth.currentUser;

      if (user == null) {
        throw Exception(
          'You are not logged in. Please sign in again.',
        );
      }

      final imageUrl = await _uploadImage();

      final metadata = user.userMetadata ?? {};

      await _service.submitReport(
        imageUrl: imageUrl,
        latitude: _latitude!,
        longitude: _longitude!,
        notes: _notesController.text.trim().isEmpty
            ? null
            : _notesController.text.trim(),
        submittedByUuid: user.id,
        reporterEmail: user.email ?? 'Not available',
        reporterName: metadata['display_name']?.toString(),
        reporterPhone: metadata['phone_number']?.toString(),
      );

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Thank you! Your report and photo '
            'have been submitted successfully.',
          ),
          duration: Duration(seconds: 3),
          behavior: SnackBarBehavior.floating,
        ),
      );

      await Future.delayed(
        const Duration(milliseconds: 1200),
      );

      if (mounted) {
        Navigator.pop(context);
      }
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Failed to submit report: $e',
          ),
          duration: const Duration(seconds: 5),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _submitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          // Background image
          Positioned.fill(
            child: Image.network(
              'https://thumbs.dreamstime.com/b/'
              'australian-map-icons-set-sketch-your-'
              'design-vector-illustration-89863077.jpg',
              fit: BoxFit.cover,
              errorBuilder: (
                context,
                error,
                stackTrace,
              ) {
                return Container(
                  color: const Color(0xFF050505),
                );
              },
            ),
          ),

          // Dark overlay keeps the map texture subtle and readable.
          Positioned.fill(
            child: Container(
              color: const Color(0xFF050505).withValues(alpha: 0.93),
            ),
          ),

          SafeArea(
            child: Column(
              children: [
                // Page header
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                  child: Row(
                    children: [
                      IconButton(
                        icon: const Icon(
                          Icons.arrow_back,
                          color: Colors.white,
                        ),
                        onPressed: () {
                          Navigator.maybePop(
                            context,
                          );
                        },
                      ),
                      const Expanded(
                        child: Column(
                          children: [
                            Text(
                              'Report Graffiti',
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 20,
                                color: Colors.white,
                              ),
                            ),
                            SizedBox(height: 2),
                            Text(
                              '🇦🇺 Be the reason Australia’s '
                              'streets look better tomorrow.',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w500,
                                color: Color(0xFF8E8E95),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 48),
                    ],
                  ),
                ),

                Expanded(
                  child: ListView(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 20,
                      vertical: 8,
                    ),
                    children: [
                      // Photo section
                      _PurpleCard(
                        title: 'Step 1: Add Evidence Photo',
                        icon: Icons.camera_alt_rounded,
                        child: Column(
                          children: [
                            if (_capturedImage != null)
                              _CapturedPhotoBadge(
                                fileName: _capturedImage!.name,
                                image: _capturedImage!,
                              )
                            else
                              const _EmptyPhotoPlaceholder(),
                            const SizedBox(
                              height: 12,
                            ),
                            SizedBox(
                              width: double.infinity,
                              height: 48,
                              child: ElevatedButton.icon(
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.white,
                                  elevation: 0,
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(
                                      16,
                                    ),
                                  ),
                                ),
                                onPressed: _submitting ? null : _pickImage,
                                icon: const Icon(
                                  Icons.camera_alt_rounded,
                                  color: _purpleAccent,
                                  size: 20,
                                ),
                                label: Text(
                                  _capturedImage == null
                                      ? 'Take Photo'
                                      : 'Retake Photo',
                                  style: const TextStyle(
                                    color: _purpleAccent,
                                    fontWeight: FontWeight.w700,
                                    fontSize: 14,
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 16),

                      // Location section
                      _PurpleCard(
                        title: 'Step 2: Select Location',
                        icon: Icons.location_on_rounded,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: _LocationButton(
                                    label: 'Current Location',
                                    icon: Icons.my_location_rounded,
                                    onPressed: _useCurrentLocation,
                                  ),
                                ),
                                const SizedBox(
                                  width: 10,
                                ),
                                Expanded(
                                  child: _LocationButton(
                                    label: 'Pick on Map',
                                    icon: Icons.map_rounded,
                                    onPressed: _pickOnMap,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(
                              height: 14,
                            ),
                            Center(
                              child: Text(
                                _latitude != null && _longitude != null
                                    ? 'Selected: '
                                        '${_latitude!.toStringAsFixed(5)}, '
                                        '${_longitude!.toStringAsFixed(5)}'
                                    : 'No location selected yet.',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  color: _latitude != null
                                      ? Colors.white
                                      : Colors.white.withValues(
                                          alpha: 0.7,
                                        ),
                                  fontWeight: _latitude != null
                                      ? FontWeight.w700
                                      : FontWeight.w500,
                                  fontSize: 13,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 16),

                      // Notes section
                      _PurpleCard(
                        title: 'Step 3: Notes / Remarks',
                        icon: Icons.edit_note_rounded,
                        child: TextField(
                          controller: _notesController,
                          maxLines: 3,
                          enabled: !_submitting,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                          ),
                          decoration: InputDecoration(
                            filled: true,
                            fillColor: Colors.white.withValues(
                              alpha: 0.15,
                            ),
                            hintText: 'Additional details for '
                                'council staff (optional)',
                            hintStyle: TextStyle(
                              color: Colors.white.withValues(
                                alpha: 0.6,
                              ),
                              fontSize: 13,
                            ),
                            contentPadding: const EdgeInsets.all(
                              16,
                            ),
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
                                color: Colors.white,
                                width: 1.5,
                              ),
                            ),
                          ),
                        ),
                      ),

                      const SizedBox(height: 16),

                      // Consent section
                      _PurpleCard(
                        title: 'Confirmation & Consent',
                        icon: Icons.verified_user_rounded,
                        child: InkWell(
                          onTap: _submitting
                              ? null
                              : () {
                                  setState(() {
                                    _isConfirmed = !_isConfirmed;
                                  });
                                },
                          borderRadius: BorderRadius.circular(
                            12,
                          ),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                              vertical: 4,
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                SizedBox(
                                  height: 24,
                                  width: 24,
                                  child: Checkbox(
                                    value: _isConfirmed,
                                    activeColor: Colors.white,
                                    checkColor: _purpleAccent,
                                    side: BorderSide(
                                      color: Colors.white.withValues(
                                        alpha: 0.8,
                                      ),
                                      width: 1.5,
                                    ),
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(
                                        4,
                                      ),
                                    ),
                                    onChanged: _submitting
                                        ? null
                                        : (value) {
                                            setState(
                                              () {
                                                _isConfirmed = value ?? false;
                                              },
                                            );
                                          },
                                  ),
                                ),
                                const SizedBox(
                                  width: 12,
                                ),
                                const Expanded(
                                  child: Text(
                                    'I confirm that the '
                                    'information provided is '
                                    'true and accurate to the '
                                    'best of my knowledge. By '
                                    'submitting this report, I '
                                    'grant permission for the '
                                    'submitted photo to be '
                                    'used, stored, and shared '
                                    'with relevant authorities '
                                    'for the purpose of '
                                    'assessing, managing, and '
                                    'resolving the reported '
                                    'graffiti.',
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontSize: 12.5,
                                      height: 1.4,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),

                      const SizedBox(height: 28),

                      // Submit button
                      SizedBox(
                        height: 56,
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: _canSubmit
                                ? _purpleAccent
                                : const Color(0xFF25252A),
                            elevation: _canSubmit ? 6 : 0,
                            shadowColor: _purpleAccent.withValues(
                              alpha: 0.4,
                            ),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(
                                18,
                              ),
                            ),
                          ),
                          onPressed:
                              _canSubmit && !_submitting ? _submit : null,
                          child: _submitting
                              ? const Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    SizedBox(
                                      height: 22,
                                      width: 22,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2.5,
                                        color: Colors.white,
                                      ),
                                    ),
                                    SizedBox(width: 12),
                                    Text(
                                      'Uploading...',
                                      style: TextStyle(
                                        color: Colors.white,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ],
                                )
                              : Text(
                                  'Submit Report',
                                  style: TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                    color: _canSubmit
                                        ? Colors.white
                                        : Colors.white70,
                                    letterSpacing: 0.3,
                                  ),
                                ),
                        ),
                      ),

                      const SizedBox(height: 20),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// Reusable dark card with a subtle purple glow.
class _PurpleCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final Widget child;

  const _PurpleCard({
    required this.title,
    required this.icon,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [
            Color(0xFF19151F),
            Color(0xFF111114),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFF372447)),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFFA855F7).withValues(alpha: 0.14),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(
                  icon,
                  size: 20,
                  color: Colors.white,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                    color: Colors.white,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          child,
        ],
      ),
    );
  }
}

// Web-compatible photo preview
class _CapturedPhotoBadge extends StatelessWidget {
  final String fileName;
  final XFile image;

  const _CapturedPhotoBadge({
    required this.fileName,
    required this.image,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: FutureBuilder<Uint8List>(
              future: image.readAsBytes(),
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return Container(
                    width: 70,
                    height: 70,
                    color: Colors.white.withValues(alpha: 0.15),
                    child: const Center(
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    ),
                  );
                }

                if (snapshot.hasError || snapshot.data == null) {
                  return Container(
                    width: 70,
                    height: 70,
                    color: Colors.white.withValues(alpha: 0.15),
                    child: const Icon(
                      Icons.image_not_supported_outlined,
                      color: Colors.white,
                    ),
                  );
                }

                return Image.memory(
                  snapshot.data!,
                  width: 70,
                  height: 70,
                  fit: BoxFit.cover,
                );
              },
            ),
          ),
          const SizedBox(width: 12),
          const Icon(
            Icons.check_circle_rounded,
            color: Colors.greenAccent,
            size: 20,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Photo captured: $fileName',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptyPhotoPlaceholder extends StatelessWidget {
  const _EmptyPhotoPlaceholder();

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 90,
      width: double.infinity,
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.add_a_photo_outlined,
            size: 28,
            color: Colors.white.withValues(alpha: 0.7),
          ),
          const SizedBox(height: 6),
          Text(
            'No photo attached yet',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.7),
              fontSize: 13,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class _LocationButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onPressed;

  const _LocationButton({
    required this.label,
    required this.icon,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 48,
      child: TextButton.icon(
        style: TextButton.styleFrom(
          backgroundColor: Colors.white.withValues(
            alpha: 0.08,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
        ),
        onPressed: onPressed,
        icon: Icon(
          icon,
          size: 18,
          color: Colors.white,
        ),
        label: Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            color: Colors.white,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }
}
