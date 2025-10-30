const { Builder, By, until, Key } = require('selenium-webdriver');
const fs = require('fs');
const csv = require('csv-parser');
const { createObjectCsvWriter } = require('csv-writer');

const CONFIG = {
  headless: false,
  searchTimeout: 25000,
  browserDelay: 3000,
  scrollAttempts: 5,
  waitForResults: 3000
};

class SmartRevenueBot {
  constructor() {
    this.driver = null;
    this.results = [];
    this.originalData = [];
  }

  async init() {
    console.log('🚀 Launching Chrome Browser...\n');
    this.driver = await new Builder()
      .forBrowser('chrome')
      .build();
    
    await this.driver.manage().window().maximize();
    console.log('✓ Chrome opened\n');
  }

  async sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async scrollAndWait() {
    console.log('   📜 Scrolling and loading all content...');
    // Scroll down slowly to trigger lazy loading
    for (let i = 0; i < CONFIG.scrollAttempts; i++) {
      await this.driver.executeScript('window.scrollBy(0, 400)');
      await this.sleep(1000);
    }
    // Scroll back to top to scan from beginning
    await this.driver.executeScript('window.scrollTo(0, 0)');
    await this.sleep(800);
    // Scroll to middle
    await this.driver.executeScript('window.scrollTo(0, document.body.scrollHeight / 2)');
    await this.sleep(800);
  }

  async searchCompanyRevenue(company, rowIndex) {
    try {
      console.log(`\n${'='.repeat(70)}`);
      console.log(`[Row ${rowIndex}] 🎯 Searching: ${company}`);
      console.log('='.repeat(70));
      
      await this.driver.get('https://duckduckgo.com');
      await this.sleep(1500);

      const searchBox = await this.driver.wait(
        until.elementLocated(By.id('searchbox_input')),
        CONFIG.searchTimeout
      );
      
      const query = `"${company}" revenue 2024 2025`;
      console.log(`[Row ${rowIndex}] ⌨️  Typing: ${query}`);
      
      await searchBox.clear();
      await searchBox.sendKeys(query);
      await this.sleep(1000);
      await searchBox.sendKeys(Key.RETURN);

      console.log(`[Row ${rowIndex}] ⏳ Waiting for results...`);
      
      await this.driver.wait(
        until.elementLocated(By.css('[data-testid="result"]')),
        CONFIG.searchTimeout
      );
      
      await this.sleep(CONFIG.waitForResults);
      await this.scrollAndWait();

      console.log(`[Row ${rowIndex}] 🔍 Deep scanning entire page...`);
      
      // Extract ALL text from the page including hidden/small elements
      const pageData = await this.driver.executeScript(() => {
        // Get all text nodes, including small font sizes
        const allText = [];
        
        // Method 1: Get body text
        allText.push(document.body.innerText);
        
        // Method 2: Get all paragraph and div text (catches small fonts)
        document.querySelectorAll('p, div, span, li, td, a, h1, h2, h3, h4, h5, h6').forEach(el => {
          const text = el.textContent;
          if (text && text.trim().length > 0) {
            allText.push(text.trim());
          }
        });
        
        // Method 3: Get meta descriptions (sometimes revenue is there)
        const metaDesc = document.querySelector('meta[name="description"]');
        if (metaDesc) {
          allText.push(metaDesc.content);
        }
        
        // Method 4: Get all visible text with computed styles
        const allElements = document.querySelectorAll('*');
        allElements.forEach(el => {
          const style = window.getComputedStyle(el);
          // Include even small fonts (as small as 8px)
          if (style.fontSize && parseFloat(style.fontSize) >= 8) {
            const text = el.textContent;
            if (text && text.length > 10 && text.length < 500) {
              allText.push(text.trim());
            }
          }
        });
        
        return allText.join(' | ');
      });

      const revenue = this.extractRevenue(pageData, rowIndex);

      if (revenue) {
        console.log(`[Row ${rowIndex}] ✅ FOUND: ${revenue}\n`);
        return { company, revenue, status: 'Found' };
      }

      console.log(`[Row ${rowIndex}] 🔄 Trying alternative search...`);
      const altRevenue = await this.alternativeSearch(company, rowIndex);
      
      if (altRevenue) {
        return { company, revenue: altRevenue, status: 'Found' };
      }

      console.log(`[Row ${rowIndex}] ❌ Revenue not found\n`);
      return { company, revenue: 'Not Found', status: 'Failed' };

    } catch (error) {
      console.log(`[Row ${rowIndex}] ✗ Error: ${error.message}\n`);
      return { company, revenue: 'Error', status: 'Failed' };
    }
  }

  async alternativeSearch(company, rowIndex) {
    try {
      await this.driver.get('https://duckduckgo.com');
      await this.sleep(1500);

      const searchBox = await this.driver.findElement(By.id('searchbox_input'));
      const query = `${company} annual revenue latest`;
      
      console.log(`[Row ${rowIndex}] ⌨️  Alternative: ${query}`);
      await searchBox.clear();
      await searchBox.sendKeys(query);
      await this.sleep(1000);
      await searchBox.sendKeys(Key.RETURN);

      await this.driver.wait(
        until.elementLocated(By.css('[data-testid="result"]')),
        CONFIG.searchTimeout
      );
      
      await this.sleep(CONFIG.waitForResults);
      await this.scrollAndWait();

      console.log(`[Row ${rowIndex}] 🔍 Deep scanning alternative results...`);
      
      // Deep scan for alternative search too
      const pageData = await this.driver.executeScript(() => {
        const allText = [];
        allText.push(document.body.innerText);
        
        document.querySelectorAll('p, div, span, li, td, a, h1, h2, h3, h4, h5, h6').forEach(el => {
          const text = el.textContent;
          if (text && text.trim().length > 0) {
            allText.push(text.trim());
          }
        });
        
        const metaDesc = document.querySelector('meta[name="description"]');
        if (metaDesc) allText.push(metaDesc.content);
        
        return allText.join(' | ');
      });

      const revenue = this.extractRevenue(pageData, rowIndex);
      
      if (revenue) {
        console.log(`[Row ${rowIndex}] ✅ FOUND (Alt): ${revenue}\n`);
        return revenue;
      }

      return null;

    } catch (error) {
      console.log(`[Row ${rowIndex}] ⚠️  Alternative failed`);
      return null;
    }
  }

  extractRevenue(text, rowIndex) {
    // Enhanced patterns - more comprehensive
    const patterns = [
      // Most specific: Year + Revenue
      /(?:fiscal|FY|year)?\s*202[3-5]\s+(?:annual\s+)?revenue[:\s]*(?:was|is|of)?\s*(?:approximately|around|about)?\s*\$?\s*([\d,]+(?:\.\d+)?)\s*(billion|million|B|M|bn|mn)/gi,
      /revenue\s+(?:for|in|of)?\s+(?:fiscal|FY)?\s*202[3-5][:\s]*(?:was|is)?\s*\$?\s*([\d,]+(?:\.\d+)?)\s*(billion|million|B|M|bn|mn)/gi,
      
      // Annual revenue patterns
      /annual\s+revenue[:\s]*(?:is|was|of|approximately)?\s*\$?\s*([\d,]+(?:\.\d+)?)\s*(billion|million|B|M|bn|mn)/gi,
      /total\s+revenue[:\s]*(?:is|was|of)?\s*\$?\s*([\d,]+(?:\.\d+)?)\s*(billion|million|B|M|bn|mn)/gi,
      /(?:company|firm)\s+revenue[:\s]*\$?\s*([\d,]+(?:\.\d+)?)\s*(billion|million|B|M)/gi,
      
      // Revenue with descriptors
      /(?:generated|reported|recorded|posted)\s+revenue\s+of\s+\$?\s*([\d,]+(?:\.\d+)?)\s*(billion|million|B|M)/gi,
      /revenue\s+(?:reached|hit|topped|exceeded)\s+\$?\s*([\d,]+(?:\.\d+)?)\s*(billion|million|B|M)/gi,
      
      // Dollar first patterns
      /\$\s*([\d,]+(?:\.\d+)?)\s*(billion|B|bn)\s+(?:in\s+)?(?:annual\s+)?revenue/gi,
      /\$\s*([\d,]+(?:\.\d+)?)\s*(million|M|mn)\s+(?:in\s+)?(?:annual\s+)?revenue/gi,
      
      // General revenue patterns
      /revenue[:\s]+(?:of\s+)?\$?\s*([\d,]+(?:\.\d+)?)\s*(billion|million|B|M|bn|mn)/gi,
      /revenues?[:\s]+\$?\s*([\d,]+(?:\.\d+)?)\s*(billion|million|B|M)/gi,
      
      // Loose patterns (last resort)
      /\$\s*([\d,]+(?:\.\d+)?)\s*(billion|B|bn)(?!\s+market)/gi,
      /\$\s*([\d,]+(?:\.\d+)?)\s*(million|M|mn)(?!\s+funding|investment|valuation)/gi,
      
      // International formats
      /revenue.*?USD\s*([\d,]+(?:\.\d+)?)\s*(billion|million|B|M)/gi,
      /turnover.*?\$?\s*([\d,]+(?:\.\d+)?)\s*(billion|million)/gi
    ];

    const foundMatches = [];
    const seenValues = new Set(); // Avoid duplicates

    for (const pattern of patterns) {
      pattern.lastIndex = 0;
      const matches = [...text.matchAll(pattern)];
      
      for (const match of matches) {
        if (match[1] && match[2]) {
          const number = match[1].replace(/,/g, '');
          const unit = match[2].toLowerCase();
          const value = parseFloat(number);
          
          // Create unique key to avoid duplicates
          const uniqueKey = `${value}-${unit}`;
          if (seenValues.has(uniqueKey)) continue;
          
          // Validate reasonable revenue ranges
          if (unit.includes('b') && value >= 0.001 && value <= 50000) {
            const revenue = `${match[1]} billion`;
            foundMatches.push({ 
              revenue, 
              value, 
              unit: 'billion',
              context: match[0],
              priority: this.getPriority(match[0])
            });
            seenValues.add(uniqueKey);
          } else if ((unit.includes('m') || unit.includes('mn')) && value >= 0.1 && value <= 1000000) {
            const revenue = `${match[1]} million`;
            foundMatches.push({ 
              revenue, 
              value, 
              unit: 'million',
              context: match[0],
              priority: this.getPriority(match[0])
            });
            seenValues.add(uniqueKey);
          }
        }
      }
    }

    if (foundMatches.length > 0) {
      console.log(`[Row ${rowIndex}] 💰 Found ${foundMatches.length} potential revenue figure(s)`);
      
      // Sort by priority (year-specific first, then by unit)
      foundMatches.sort((a, b) => {
        if (a.priority !== b.priority) return b.priority - a.priority;
        if (a.unit === 'billion' && b.unit === 'million') return -1;
        if (a.unit === 'million' && b.unit === 'billion') return 1;
        return b.value - a.value;
      });
      
      // Log the best match context
      console.log(`[Row ${rowIndex}] 📝 Best match: "${foundMatches[0].context}"`);
      
      return foundMatches[0].revenue;
    }

    return null;
  }

  getPriority(context) {
    // Give higher priority to more specific contexts
    const lower = context.toLowerCase();
    if (lower.includes('2024') || lower.includes('2025')) return 10;
    if (lower.includes('2023')) return 9;
    if (lower.includes('annual revenue')) return 8;
    if (lower.includes('total revenue')) return 7;
    if (lower.includes('fiscal')) return 7;
    if (lower.includes('reported') || lower.includes('generated')) return 6;
    return 5;
  }

  async readCSV(filePath) {
    return new Promise((resolve, reject) => {
      const companies = [];
      let rowIndex = 0;
      
      fs.createReadStream(filePath)
        .pipe(csv())
        .on('data', (row) => {
          this.originalData.push(row);
          
          const companyName = row['company_name'] || Object.values(row)[0];
          
          if (companyName && companyName.trim().length > 0) {
            companies.push({ name: companyName.trim(), row: rowIndex });
          }
          rowIndex++;
        })
        .on('end', () => {
          console.log(`✓ Loaded ${companies.length} companies\n`);
          resolve(companies);
        })
        .on('error', reject);
    });
  }

  async writeResults(results) {
    const mergedData = this.originalData.map((row) => {
      const companyName = row['company_name'] || Object.values(row)[0];
      const revenueData = results.find(r => r.company === companyName);
      
      return {
        company_name: companyName,
        revenue: revenueData ? revenueData.revenue : 'Not Found',
        revenueStatus: revenueData ? revenueData.status : 'Not Processed'
      };
    });

    const csvWriter = createObjectCsvWriter({
      path: 'output_with_revenue.csv',
      header: [
        { id: 'company_name', title: 'company_name' },
        { id: 'revenue', title: 'revenue' },
        { id: 'revenueStatus', title: 'revenueStatus' }
      ]
    });

    await csvWriter.writeRecords(mergedData);
    console.log('\n✅ Results saved to: output_with_revenue.csv\n');
  }

  async saveBackup(results) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const backupFile = `backup_${timestamp}.json`;
    
    try {
      fs.writeFileSync(backupFile, JSON.stringify(results, null, 2));
    } catch (error) {
      console.error('Backup error:', error);
    }
  }

  async loadPreviousBackup() {
    try {
      const files = fs.readdirSync('.').filter(f => f.startsWith('backup_') && f.endsWith('.json'));
      
      if (files.length > 0) {
        const latestBackup = files.sort().reverse()[0];
        const backupData = JSON.parse(fs.readFileSync(latestBackup, 'utf8'));
        
        if (this.originalData.length > 0) {
          const firstCompany = this.originalData[0]['company_name'] || Object.values(this.originalData[0])[0];
          const backupHasCompany = backupData.find(r => r.company === firstCompany);
          
          if (!backupHasCompany) {
            fs.unlinkSync(latestBackup);
            return [];
          }
        }
        
        console.log(`✅ Loaded ${backupData.length} previous results\n`);
        return backupData;
      }
    } catch (error) {
      console.log(`Backup load error: ${error.message}`);
    }
    return [];
  }

  async processCompanies(companies) {
    console.log(`\n${'='.repeat(70)}`);
    console.log(`📊 SMART REVENUE EXTRACTION`);
    console.log(`Processing: ${companies.length} companies`);
    console.log(`${'='.repeat(70)}\n`);
    
    for (let i = 0; i < companies.length; i++) {
      const comp = companies[i];
      const result = await this.searchCompanyRevenue(comp.name, comp.row);
      this.results.push(result);
      
      await this.saveBackup(this.results);
      
      if (i < companies.length - 1) {
        console.log(`⏳ Waiting (${i + 1}/${companies.length})...\n`);
        await this.sleep(CONFIG.browserDelay);
      }
    }
  }

  async close() {
    if (this.driver) {
      await this.sleep(1000);
      await this.driver.quit();
      console.log('✓ Browser closed');
    }
  }

  printSummary() {
    const found = this.results.filter(r => r.status === 'Found').length;
    const failed = this.results.filter(r => r.status === 'Failed').length;
    
    console.log('\n' + '='.repeat(70));
    console.log('📈 FINAL RESULTS');
    console.log('='.repeat(70));
    console.log(`Total: ${this.results.length}`);
    console.log(`✅ Found: ${found} (${((found / this.results.length) * 100).toFixed(1)}%)`);
    console.log(`❌ Not Found: ${failed}`);
    console.log('='.repeat(70));
  }

  async run(csvPath) {
    try {
      const startTime = Date.now();
      await this.init();
      
      const companies = await this.readCSV(csvPath);
      const previousResults = await this.loadPreviousBackup();
      
      const companiesToProcess = companies.filter(comp => 
        !previousResults.find(r => r.company === comp.name)
      );

      if (companiesToProcess.length === 0) {
        console.log('✅ All companies already processed!\n');
        this.results = previousResults;
      } else {
        console.log(`⏳ Processing ${companiesToProcess.length} companies\n`);
        await this.processCompanies(companiesToProcess);
        this.results = [...previousResults, ...this.results];
      }

      await this.writeResults(this.results);
      await this.saveBackup(this.results);
      this.printSummary();
      
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      console.log(`\n✅ Completed in ${elapsed} seconds\n`);
    } catch (error) {
      console.error('❌ Error:', error.message);
      await this.saveBackup(this.results);
    } finally {
      await this.close();
    }
  }
}

const bot = new SmartRevenueBot();
const csvFile = process.argv[2] || 'input.csv';
const forceRestart = process.argv[3] === '--restart' || process.argv[3] === '-r';

if (forceRestart) {
  console.log('🔄 Deleting backups...\n');
  const backups = fs.readdirSync('.').filter(f => f.startsWith('backup_') && f.endsWith('.json'));
  backups.forEach(backup => {
    fs.unlinkSync(backup);
    console.log(`🗑️  Deleted: ${backup}`);
  });
  console.log('✅ Starting fresh...\n');
}

bot.run(csvFile);