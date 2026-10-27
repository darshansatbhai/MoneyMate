document.addEventListener('DOMContentLoaded', () => {
  function splitTextNodesRecursive(element, startIndex) {
    const childNodes = Array.from(element.childNodes);
    let charIndex = startIndex;
    
    childNodes.forEach(child => {
      if (child.nodeType === 3) {
        const text = child.nodeValue;
        const fragment = document.createDocumentFragment();
        
        // Split by whitespace but keep the whitespace in the array
        const words = text.split(/(\s+)/);
        
        words.forEach(word => {
          if (word.trim() === '') {
            // It's just whitespace, keep it as text node
            fragment.appendChild(document.createTextNode(word));
          } else {
            // It's a word, wrap in a container to prevent mid-word wrapping
            const wordSpan = document.createElement('span');
            wordSpan.style.display = 'inline-block';
            
            for (let i = 0; i < word.length; i++) {
              const charSpan = document.createElement('span');
              charSpan.className = 'char';
              // Slow down the letter typing effect
              charSpan.style.transitionDelay = (charIndex * 0.035) + 's';
              charSpan.textContent = word[i];
              wordSpan.appendChild(charSpan);
              charIndex++;
            }
            fragment.appendChild(wordSpan);
          }
        });
        
        element.replaceChild(fragment, child);
      } else if (child.nodeType === 1 && !child.classList.contains('char')) {
        charIndex = splitTextNodesRecursive(child, charIndex);
      }
    });
    return charIndex;
  }

  document.querySelectorAll('.text-reveal').forEach(el => {
    splitTextNodesRecursive(el, 0);
  });

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('active');
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.reveal, .text-reveal').forEach((el) => {
    observer.observe(el);
  });

  // Page Transition Effect (Smooth fade between pages)
  document.body.style.opacity = '0';
  document.body.style.transition = 'opacity 0.6s ease-out';
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      document.body.style.opacity = '1';
    });
  });

  document.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', (e) => {
      // Only animate internal links that don't open in new tab and aren't anchor links
      if (link.hostname === window.location.hostname && link.target !== '_blank' && !link.getAttribute('href').startsWith('#')) {
        e.preventDefault();
        document.body.style.opacity = '0';
        setTimeout(() => {
          window.location = link.href;
        }, 500); // Wait for fade out
      }
    });
  });
});
