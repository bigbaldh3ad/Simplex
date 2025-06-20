document.addEventListener('DOMContentLoaded', function() {
  // Counter animation for stats
  const animateCounters = () => {
    const counters = [
      { element: document.getElementById('problems-solved'), target: 1243, suffix: '+' },
      { element: document.getElementById('active-users'), target: 568, suffix: '+' },
      { element: document.getElementById('accuracy-rate'), target: 99, suffix: '%' }
    ];
    
    const duration = 2000; // Animation duration in ms
    const frameDuration = 1000 / 60; // 60 fps
    const totalFrames = Math.round(duration / frameDuration);
    
    counters.forEach(counter => {
      let frame = 0;
      const countTo = counter.target;
      const element = counter.element;
      
      const counterInterval = setInterval(() => {
        frame++;
        const progress = frame / totalFrames;
        const currentCount = Math.round(countTo * progress);
        
        if (parseInt(element.innerText) !== currentCount) {
          element.innerText = currentCount + (frame === totalFrames ? counter.suffix : '');
        }
        
        if (frame === totalFrames) {
          clearInterval(counterInterval);
        }
      }, frameDuration);
    });
  };
  
  // Smooth scroll for anchor links
  const setupSmoothScroll = () => {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function(e) {
        e.preventDefault();
        
        const targetId = this.getAttribute('href');
        const targetElement = document.querySelector(targetId);
        
        if (targetElement) {
          window.scrollTo({
            top: targetElement.offsetTop - 100,
            behavior: 'smooth'
          });
        }
      });
    });
  };
  
  // Initialize animations when elements are in viewport
  const initAnimations = () => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          if (entry.target.classList.contains('stats-section')) {
            animateCounters();
          }
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });
    
    const sections = document.querySelectorAll('section');
    sections.forEach(section => {
      observer.observe(section);
    });
  };
  
  // Initialize all functions
  setupSmoothScroll();
  initAnimations();
});