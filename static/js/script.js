/**
 * Daniel John Britto - Portfolio JavaScript Engine
 * Handles Typing Animation, Scroll Reveal, Counters, Mobile Menu, AJAX Forms & Smooth Scrolling.
 */

document.addEventListener('DOMContentLoaded', () => {
    initTypingEffect();
    initScrollAnimations();
    initSkillProgressBars();
    initCounterAnimation();
    initNavbarScroll();
    initMobileMenu();
    initContactForm();
});

/* --------------------------------------------------------------------------
   1. Typing Animation
   -------------------------------------------------------------------------- */
function initTypingEffect() {
    const typingElement = document.getElementById('typing-text');
    if (!typingElement) return;

    const roles = JSON.parse(typingElement.getAttribute('data-roles') || '[]');
    let roleIndex = 0;
    let charIndex = 0;
    let isDeleting = false;
    let typeSpeed = 100;

    function type() {
        const currentRole = roles[roleIndex];

        if (isDeleting) {
            typingElement.textContent = currentRole.substring(0, charIndex - 1);
            charIndex--;
            typeSpeed = 50;
        } else {
            typingElement.textContent = currentRole.substring(0, charIndex + 1);
            charIndex++;
            typeSpeed = 100;
        }

        if (!isDeleting && charIndex === currentRole.length) {
            typeSpeed = 2000; // Pause at end
            isDeleting = true;
        } else if (isDeleting && charIndex === 0) {
            isDeleting = false;
            roleIndex = (roleIndex + 1) % roles.length;
            typeSpeed = 500; // Pause before typing next
        }

        setTimeout(type, typeSpeed);
    }

    if (roles.length > 0) {
        type();
    }
}

/* --------------------------------------------------------------------------
   2. Scroll Reveal Animations (AOS style)
   -------------------------------------------------------------------------- */
function initScrollAnimations() {
    const animatedElements = document.querySelectorAll('[data-aos]');

    const observerOptions = {
        root: null,
        rootMargin: '50px 0px 50px 0px',
        threshold: 0.01
    };

    const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('aos-animate');
                obs.unobserve(entry.target); // Trigger once
            }
        });
    }, observerOptions);

    animatedElements.forEach(el => observer.observe(el));
}

/* --------------------------------------------------------------------------
   3. Skill Progress Bar Animation
   -------------------------------------------------------------------------- */
function initSkillProgressBars() {
    const skillBars = document.querySelectorAll('.skill-bar-fill');

    const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const targetWidth = entry.target.getAttribute('data-progress');
                entry.target.style.width = `${targetWidth}%`;
                obs.unobserve(entry.target);
            }
        });
    }, { threshold: 0.2 });

    skillBars.forEach(bar => observer.observe(bar));
}

/* --------------------------------------------------------------------------
   4. Animated Counter Numbers
   -------------------------------------------------------------------------- */
function initCounterAnimation() {
    const counters = document.querySelectorAll('.counter');

    const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const counter = entry.target;
                const target = +counter.getAttribute('data-target');
                let count = 0;
                const duration = 2000; // 2 seconds
                const increment = Math.ceil(target / (duration / 30));

                const timer = setInterval(() => {
                    count += increment;
                    if (count >= target) {
                        counter.textContent = target;
                        clearInterval(timer);
                    } else {
                        counter.textContent = count;
                    }
                }, 30);

                obs.unobserve(counter);
            }
        });
    }, { threshold: 0.5 });

    counters.forEach(c => observer.observe(c));
}

/* --------------------------------------------------------------------------
   5. Sticky Navbar & Scroll Spy Active Link
   -------------------------------------------------------------------------- */
function initNavbarScroll() {
    const navbar = document.getElementById('navbar');
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-link');

    window.addEventListener('scroll', () => {
        // Sticky Header Toggle
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }

        // Active Link Spy
        let currentSectionId = '';
        sections.forEach(section => {
            const sectionTop = section.offsetTop - 100;
            const sectionHeight = section.offsetHeight;
            if (window.scrollY >= sectionTop && window.scrollY < sectionTop + sectionHeight) {
                currentSectionId = section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${currentSectionId}`) {
                link.classList.add('active');
            }
        });
    });
}

/* --------------------------------------------------------------------------
   6. Mobile Menu Navigation
   -------------------------------------------------------------------------- */
function initMobileMenu() {
    const mobileToggle = document.getElementById('mobile-toggle');
    const navMenu = document.getElementById('nav-menu');
    const navLinks = document.querySelectorAll('.nav-link');

    if (!mobileToggle || !navMenu) return;

    mobileToggle.addEventListener('click', () => {
        mobileToggle.classList.toggle('open');
        navMenu.classList.toggle('active');
        document.body.classList.toggle('no-scroll');
    });

    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            mobileToggle.classList.remove('open');
            navMenu.classList.remove('active');
            document.body.classList.remove('no-scroll');
        });
    });
}

/* --------------------------------------------------------------------------
   7. AJAX Contact Form Submission
   -------------------------------------------------------------------------- */
function initContactForm() {
    const form = document.getElementById('contact-form');
    const alertBox = document.getElementById('contact-alert');
    const submitBtn = document.getElementById('submit-btn');

    if (!form || !alertBox || !submitBtn) return;

    const btnText = submitBtn.querySelector('.btn-text');
    const btnIcon = submitBtn.querySelector('.btn-icon');
    const btnSpinner = submitBtn.querySelector('.btn-spinner');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // UI Loading State
        submitBtn.disabled = true;
        btnText.textContent = 'Sending...';
        if (btnIcon) btnIcon.style.display = 'none';
        if (btnSpinner) btnSpinner.style.display = 'inline-block';
        alertBox.style.display = 'none';

        const formData = new FormData(form);

        try {
            const response = await fetch(form.action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            });

            const data = await response.json();

            if (response.ok && data.success) {
                alertBox.className = 'alert-banner alert-success';
                alertBox.textContent = data.message;
                alertBox.style.display = 'block';
                form.reset();
            } else {
                alertBox.className = 'alert-banner alert-error';
                alertBox.textContent = data.message || 'An error occurred while submitting your message.';
                alertBox.style.display = 'block';
            }
        } catch (err) {
            alertBox.className = 'alert-banner alert-error';
            alertBox.textContent = 'Network error. Please check your connection and try again.';
            alertBox.style.display = 'block';
        } finally {
            // Restore UI State
            submitBtn.disabled = false;
            btnText.textContent = 'Send Message';
            if (btnIcon) btnIcon.style.display = 'inline-block';
            if (btnSpinner) btnSpinner.style.display = 'none';
        }
    });
}
