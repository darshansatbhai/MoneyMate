"use client"
import { useEffect, useState } from 'react'
import { supabaseClient } from '@/lib/supabaseClient'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, RadialBarChart, RadialBar, Legend } from 'recharts'
import { ArrowDownLeft, ArrowUpRight, Wallet, Download, Search, Filter } from 'lucide-react'

const COLORS = ['#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6']

const DEMO_TXS = [
  { id: "1", amount: 45000, category: "Salary", transaction_type: "income", description: "Monthly Salary Credited", created_at: new Date(Date.now() - 86400000 * 1).toISOString() },
  { id: "2", amount: 850, category: "Food", transaction_type: "expense", description: "Dinner with Friends at Cafe", created_at: new Date(Date.now() - 86400000 * 1).toISOString() },
  { id: "3", amount: 350, category: "Travel", transaction_type: "expense", description: "Uber cab to office", created_at: new Date(Date.now() - 86400000 * 2).toISOString() },
  { id: "4", amount: 1200, category: "Bills", transaction_type: "expense", description: "Electricity Bill payment", created_at: new Date(Date.now() - 86400000 * 3).toISOString() },
  { id: "5", amount: 2400, category: "Shopping", transaction_type: "expense", description: "Pantaloons clothes shopping", created_at: new Date(Date.now() - 86400000 * 4).toISOString() },
  { id: "6", amount: 1500, category: "Health", transaction_type: "expense", description: "Gym membership & supplements", created_at: new Date(Date.now() - 86400000 * 5).toISOString() },
  { id: "7", amount: 600, category: "Entertainment", transaction_type: "expense", description: "Movie tickets & popcorn", created_at: new Date(Date.now() - 86400000 * 6).toISOString() },
  { id: "8", amount: 1000, category: "Other", transaction_type: "lent", description: "[Rahul] Movie & Dinner split", created_at: new Date(Date.now() - 86400000 * 7).toISOString() },
  { id: "9", amount: 800, category: "Other", transaction_type: "settle_received", description: "[Rahul] Rahul paid back for dinner", created_at: new Date(Date.now() - 86400000 * 8).toISOString() },
  { id: "10", amount: 200, category: "Travel", transaction_type: "borrowed", description: "[Sneha] Cab fare borrowed", created_at: new Date(Date.now() - 86400000 * 9).toISOString() },
  { id: "11", amount: 120, category: "Food", transaction_type: "expense", description: "Chai & Samosa snacks", created_at: new Date(Date.now() - 86400000 * 10).toISOString() },
  { id: "12", amount: 3000, category: "Freelance", transaction_type: "income", description: "UI Design gig payment", created_at: new Date(Date.now() - 86400000 * 11).toISOString() }
];

export default function DashboardClient({ userId, userName, isDemo }: { userId: string, userName: string, isDemo?: boolean }) {
  const [txs, setTxs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState('all')
  const [sortType, setSortType] = useState('date_desc')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [isSortDropdownOpen, setIsSortDropdownOpen] = useState(false)

  const fetchTxs = async () => {
    if (isDemo || userId === 'demo') {
      setTxs(DEMO_TXS)
      setLoading(false)
      return
    }

    try {
      const { data } = await supabaseClient
        .from('transactions')
        .select('*')
        .eq('user_id', userId)
        .order('created_at', { ascending: false })
      
      if (data) setTxs(data)
    } catch (e) {
      console.warn("Supabase fetch failed, falling back to demo data", e)
      setTxs(DEMO_TXS)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTxs()
    if (isDemo || userId === 'demo') return

    const interval = setInterval(fetchTxs, 10000)
    return () => clearInterval(interval)
  }, [userId, isDemo])

  if (loading) return <div className="flex h-screen items-center justify-center">Loading your dashboard...</div>

  let totalIncome = 0
  let totalExpense = 0
  const categories: Record<string, number> = {}
  const balances: Record<string, number> = {}

  // Parse mapped fields
  const parsedTxs = txs.map(tx => {
    let person = ''
    let note = tx.description || ''
    if (note.startsWith('[') && note.includes(']')) {
      person = note.substring(1, note.indexOf(']'))
      note = note.substring(note.indexOf(']') + 1).trim()
    }
    return { ...tx, type: tx.transaction_type, person, note }
  })

  parsedTxs.forEach(tx => {
    const amount = Number(tx.amount)
    if (tx.type === 'income' || tx.type === 'borrowed' || tx.type === 'settle_received') {
      totalIncome += amount
    } else {
      totalExpense += amount
      categories[tx.category] = (categories[tx.category] || 0) + amount
    }

    if (tx.person) {
      const p = tx.person.toLowerCase()
      if (!balances[p]) balances[p] = 0
      if (tx.type === 'lent' || tx.type === 'settle_paid') balances[p] += amount
      if (tx.type === 'borrowed' || tx.type === 'settle_received') balances[p] -= amount
    }
  })

  const pieData = Object.entries(categories).map(([name, value], i) => ({ 
    name, 
    value, 
    fill: COLORS[i % COLORS.length] 
  }))

  const filteredTxs = parsedTxs.filter(tx => {
    // Search match
    const q = searchQuery.toLowerCase()
    const matchesSearch = !q || 
      tx.category.toLowerCase().includes(q) || 
      (tx.person && tx.person.toLowerCase().includes(q)) || 
      (tx.note && tx.note.toLowerCase().includes(q)) || 
      tx.amount.toString().includes(q)

    // Filter match
    let matchesFilter = true
    if (filterType === 'income') matchesFilter = ['income', 'settle_received'].includes(tx.type)
    if (filterType === 'expense') matchesFilter = ['expense', 'settle_paid'].includes(tx.type)
    if (filterType === 'borrowed') matchesFilter = tx.type === 'borrowed'
    if (filterType === 'lent') matchesFilter = tx.type === 'lent'

    // Date range match
    let matchesDate = true
    const txDate = new Date(tx.created_at)
    if (startDate) {
      const start = new Date(startDate)
      start.setHours(0, 0, 0, 0)
      if (txDate < start) matchesDate = false
    }
    if (endDate) {
      const end = new Date(endDate)
      end.setHours(23, 59, 59, 999)
      if (txDate > end) matchesDate = false
    }

    return matchesSearch && matchesFilter && matchesDate
  })

  const sortedTxs = [...filteredTxs].sort((a, b) => {
    if (sortType === 'date_desc') return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    if (sortType === 'date_asc') return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    if (sortType === 'amount_desc') return Number(b.amount) - Number(a.amount)
    if (sortType === 'amount_asc') return Number(a.amount) - Number(b.amount)
    return 0
  })

  const exportStatement = async () => {
    let logoData: string | null = null;
    try {
      const res = await fetch('/logo-128.png');
      const blob = await res.blob();
      logoData = await new Promise((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result as string);
        reader.readAsDataURL(blob);
      });
    } catch(e) {}

    import('jspdf').then(jsPDF => {
      import('jspdf-autotable').then(autoTable => {
        const doc = new jsPDF.default();
        
        // Setup colors to match dashboard theme
        const primaryColor = [31, 28, 24] as [number, number, number]; // #1F1C18 (Dark text)
        const accentColor = [42, 171, 238] as [number, number, number]; // #2AABEE (Cyan)
        const lightBeige = [243, 241, 237] as [number, number, number]; // #F3F1ED
        const textGray = [126, 120, 112] as [number, number, number]; // #7E7870
        
        // --- Header Section ---
        // Top banner (Beige background)
        doc.setFillColor(...lightBeige);
        doc.rect(0, 0, 210, 30, 'F');
        
        if (logoData) {
          doc.addImage(logoData, 'PNG', 14, 8, 14, 14);
        }
        
        // "Money Mate" logo text
        doc.setTextColor(...primaryColor);
        doc.setFontSize(24);
        doc.setFont('times', 'bold');
        doc.text('Money', logoData ? 32 : 14, 18);
        
        const moneyWidth = doc.getTextWidth('Money ');
        doc.setTextColor(...accentColor);
        doc.setFont('times', 'italic');
        doc.text('Mate', (logoData ? 32 : 14) + moneyWidth, 18);
        
        doc.setTextColor(...textGray);
        doc.setFontSize(9);
        doc.setFont('helvetica', 'normal');
        doc.text('Dashboard Statement', 196, 18, { align: 'right' });
        
        // Title
        doc.setTextColor(...primaryColor);
        doc.setFontSize(16);
        doc.setFont('helvetica', 'bold');
        doc.text('STATEMENT OF ACCOUNT', 14, 45);
        
        // User Info Box
        doc.setFillColor(255, 255, 255);
        doc.setDrawColor(...lightBeige);
        doc.roundedRect(14, 50, 90, 35, 3, 3, 'FD');
        
        doc.setFontSize(9);
        doc.setTextColor(...textGray);
        doc.text('ACCOUNT HOLDER', 18, 58);
        doc.setTextColor(...primaryColor);
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(12);
        doc.text(userName.toUpperCase(), 18, 64);
        
        doc.setFontSize(9);
        doc.setFont('helvetica', 'normal');
        doc.setTextColor(...textGray);
        doc.text('Statement Date:', 18, 72);
        doc.text('Period Covered:', 18, 78);
        
        doc.setTextColor(...primaryColor);
        doc.text(new Date().toLocaleDateString('en-IN'), 45, 72);
        doc.text('All Time', 45, 78);
        
        // Summary Box (Dark card theme)
        doc.setFillColor(...primaryColor);
        doc.roundedRect(110, 50, 86, 35, 3, 3, 'F');
        
        doc.setTextColor(255, 255, 255);
        doc.setFont('helvetica', 'bold');
        doc.text('NET BALANCE', 114, 58);
        
        doc.setFontSize(14);
        doc.text(`Rs. ${(totalIncome - totalExpense).toFixed(2)}`, 114, 66);
        
        doc.setFontSize(9);
        doc.setFont('helvetica', 'normal');
        doc.text('Total Credits:', 114, 78);
        doc.setTextColor(16, 185, 129); // Green
        doc.text(`+Rs. ${totalIncome.toFixed(2)}`, 140, 78);
        
        doc.setTextColor(255, 255, 255);
        doc.text('Total Debits:', 114, 83);
        doc.setTextColor(239, 68, 68); // Red
        doc.text(`-Rs. ${totalExpense.toFixed(2)}`, 140, 83);
        
        // --- Transactions Table ---
        const tableColumn = ['Date', 'Description', 'Credit (Rs.)', 'Debit (Rs.)', 'Balance (Rs.)'];
        
        // Sort from oldest to newest for running balance
        const sortedTxs = [...parsedTxs].reverse();
        let runningBalance = 0;
        const tableRows = sortedTxs.map(tx => {
            const isCredit = ['income', 'borrowed', 'settle_received'].includes(tx.type);
            const amt = Number(tx.amount);
            if (isCredit) {
                runningBalance += amt;
            } else {
                runningBalance -= amt;
            }
            
            let desc = `${tx.type.charAt(0).toUpperCase() + tx.type.slice(1)} - ${tx.category}`;
            if (tx.person || tx.note) {
                desc += `\n${tx.person ? '['+tx.person+'] ' : ''}${tx.note}`;
            }
            
            return [
                new Date(tx.created_at).toLocaleDateString('en-IN'),
                desc,
                isCredit ? amt.toFixed(2) : '-',
                !isCredit ? amt.toFixed(2) : '-',
                runningBalance.toFixed(2)
            ];
        });

        // Add End of Transactions row
        tableRows.push(['', '--- End of Statement ---', '', '', '']);

        autoTable.default(doc, {
          head: [tableColumn],
          body: tableRows,
          startY: 90,
          theme: 'grid', // Cleaner borders
          styles: { fontSize: 9, cellPadding: 4, font: 'helvetica' },
          headStyles: { 
            fillColor: lightBeige,
            textColor: primaryColor,
            lineColor: [230, 230, 230],
            lineWidth: 0.1,
            fontStyle: 'bold',
          },
          alternateRowStyles: {
            fillColor: [252, 251, 250]
          },
          columnStyles: {
            2: { halign: 'right', textColor: [16, 185, 129] }, // Credit
            3: { halign: 'right', textColor: [239, 68, 68] }, // Debit
            4: { halign: 'right', fontStyle: 'bold' }  // Balance
          },
          didParseCell: function (data: any) {
             if (data.row.index === tableRows.length - 1) {
                 data.cell.styles.halign = 'center';
                 data.cell.styles.fontStyle = 'italic';
                 data.cell.styles.textColor = [150, 150, 150];
             }
             if (data.section === 'body' && data.row.index !== tableRows.length - 1) {
                 if (data.column.index === 2 && data.cell.raw === '-') data.cell.styles.textColor = [200, 200, 200];
                 if (data.column.index === 3 && data.cell.raw === '-') data.cell.styles.textColor = [200, 200, 200];
             }
          },
          didDrawPage: function (data: any) {
            // Footer matching website
            const pageCount = (doc as any).internal.getNumberOfPages();
            
            doc.setFillColor(...lightBeige); 
            doc.rect(0, 280, 210, 17, 'F');
            doc.setTextColor(...textGray);
            doc.setFontSize(9);
            doc.setFont('helvetica', 'normal');
            
            doc.text('© 2026 Money Mate. All rights reserved. Made with heart for Telegram.', 14, 289);
            doc.text(`Page ${data.pageNumber} of ${pageCount}`, 196, 289, { align: 'right' });
          }
        });
        
        doc.save(`MoneyMate_Statement_${userName.replace(/\s+/g, '_')}.pdf`);
      })
    })
  }

  return (
    <div className="min-h-screen bg-[#F3F1ED] text-[#1F1C18] p-4 md:p-8 font-sans">
      <div className="max-w-5xl mx-auto space-y-8">
        
        {/* Header / Nav - Glassmorphism style from website */}
        <div className="flex flex-row items-center justify-between p-4 sm:p-6 rounded-[24px] sm:rounded-[32px] shadow-sm gap-2 sm:gap-4"
             style={{ 
               background: 'linear-gradient(135deg, rgba(255,255,255,0.6) 0%, rgba(255,255,255,0.2) 100%)',
               backdropFilter: 'blur(24px) saturate(180%)',
               WebkitBackdropFilter: 'blur(24px) saturate(180%)',
               border: '1px solid rgba(255, 255, 255, 0.5)'
             }}>
          <div className="flex items-center gap-3 sm:gap-4">
            <img src="/logo-128.png" alt="Money Mate" className="w-10 h-10 sm:w-12 sm:h-12 rounded-[10px] sm:rounded-[14px] shadow-sm bg-white shrink-0" />
            <div className="flex flex-col justify-center">
              <h1 className="text-xl sm:text-[28px] leading-none font-semibold tracking-tight text-[#1F1C18] whitespace-nowrap" style={{ fontFamily: 'var(--font-playfair), serif' }}>
                Money <span className="italic text-[#2AABEE]">Mate</span>
              </h1>
              <p className="text-[#7E7870] mt-0.5 sm:mt-1 font-medium text-[10px] sm:text-sm truncate max-w-[120px] sm:max-w-[200px]">Dashboard for {userName}</p>
            </div>
          </div>
          <button onClick={exportStatement} className="flex shrink-0 items-center justify-center gap-2 px-3 py-2 sm:px-5 sm:py-2.5 bg-[#2AABEE] text-white rounded-lg sm:rounded-xl text-xs sm:text-sm font-semibold hover:bg-[#1D8FCB] transition-colors shadow-md shadow-blue-500/20">
            <Download size={14} className="sm:w-4 sm:h-4" />
            <span className="hidden sm:inline">Download PDF</span>
            <span className="sm:hidden">PDF</span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 border border-[#E5E2DC] rounded-[24px] bg-white shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] hover:shadow-[0_8px_30px_-4px_rgba(0,0,0,0.08)] transition-shadow">
            <div className="text-sm font-semibold text-[#7E7870] mb-2 uppercase tracking-wider flex items-center gap-2"><ArrowDownLeft size={16} className="text-emerald-500"/> Total Income</div>
            <div className="text-3xl font-bold text-[#1F1C18]">₹{totalIncome.toFixed(2)}</div>
          </div>
          <div className="p-6 border border-[#E5E2DC] rounded-[24px] bg-white shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] hover:shadow-[0_8px_30px_-4px_rgba(0,0,0,0.08)] transition-shadow">
            <div className="text-sm font-semibold text-[#7E7870] mb-2 uppercase tracking-wider flex items-center gap-2"><ArrowUpRight size={16} className="text-rose-500"/> Total Spent</div>
            <div className="text-3xl font-bold text-rose-600">₹{totalExpense.toFixed(2)}</div>
          </div>
          <div className="p-6 rounded-[24px] bg-[#1F1C18] text-white shadow-[0_8px_30px_-4px_rgba(0,0,0,0.15)] hover:shadow-[0_12px_40px_-4px_rgba(0,0,0,0.2)] transition-shadow relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-white opacity-5 rounded-full blur-2xl -mr-10 -mt-10 pointer-events-none"></div>
            <div className="text-sm font-semibold text-gray-400 mb-2 uppercase tracking-wider flex items-center gap-2 relative z-10"><Wallet size={16}/> Net Balance</div>
            <div className="text-3xl font-bold text-white relative z-10">₹{(totalIncome - totalExpense).toFixed(2)}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="border border-[#E5E2DC] p-6 rounded-[24px] bg-white shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] hover:shadow-[0_8px_30px_-4px_rgba(0,0,0,0.08)] transition-shadow">
            <h2 className="text-xl font-bold mb-6 text-[#1F1C18]" style={{ fontFamily: 'var(--font-playfair), serif' }}>Spending by Category</h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart 
                  cx="35%" 
                  cy="50%" 
                  innerRadius="30%" 
                  outerRadius="100%" 
                  barSize={15} 
                  data={pieData}
                  startAngle={90}
                  endAngle={-270}
                >
                  <RadialBar
                    // @ts-ignore
                    minAngle={15}
                    background
                    clockWise
                    dataKey="value"
                    cornerRadius={10}
                    onClick={(data: any) => setSearchQuery(data.name)}
                    style={{ cursor: 'pointer' }}
                  />
                  <Tooltip formatter={(value: any) => `₹${Number(value).toFixed(2)}`} cursor={{ fill: 'transparent' }} />
                  <Legend 
                    iconSize={12} 
                    layout="vertical" 
                    verticalAlign="middle" 
                    align="right" 
                    wrapperStyle={{ right: 0 }} 
                    onClick={(data: any) => setSearchQuery(data.value)}
                    formatter={(value) => <span className="cursor-pointer hover:text-indigo-600 transition-colors">{value}</span>}
                  />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
          </div>
          
          <div className="border border-[#E5E2DC] p-6 rounded-[24px] bg-white shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] hover:shadow-[0_8px_30px_-4px_rgba(0,0,0,0.08)] transition-shadow">
            <h2 className="text-xl font-bold mb-6 text-[#1F1C18]" style={{ fontFamily: 'var(--font-playfair), serif' }}>Udhaar (Pending Splits)</h2>
            <div className="space-y-4">
              {Object.entries(balances).map(([person, bal]) => {
                if (Math.abs(bal) < 0.01) return null;
                const isPositive = bal > 0;
                return (
                  <div key={person} className="flex justify-between items-center p-3 bg-[#F3F1ED] rounded-xl">
                    <span className="font-semibold capitalize text-[#1F1C18]">{person}</span>
                    <span className={`font-bold ${isPositive ? 'text-emerald-600' : 'text-rose-600'}`}>
                      {isPositive ? `Owes you ₹${bal.toFixed(2)}` : `You owe ₹${Math.abs(bal).toFixed(2)}`}
                    </span>
                  </div>
                )
              })}
              {Object.keys(balances).length === 0 && <p className="text-[#7E7870] italic">No pending splits.</p>}
            </div>
          </div>
        </div>

        <div className="border border-[#E5E2DC] rounded-[24px] overflow-hidden bg-white shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)]">
          <div className="px-6 py-5 border-b border-[#E5E2DC] flex flex-col md:flex-row md:items-center justify-between gap-4">
            <h2 className="text-xl font-bold min-w-max text-[#1F1C18]" style={{ fontFamily: 'var(--font-playfair), serif' }}>Recent Transactions</h2>
            
            <div className="flex flex-col xl:flex-row gap-3 flex-1 xl:justify-end flex-wrap">
              {/* Date Filters */}
              <div className="flex items-center gap-2">
                <input 
                  type="date" 
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="px-3 py-2 border border-[#E5E2DC] rounded-xl text-sm bg-white text-[#1F1C18] focus:outline-none focus:ring-2 focus:ring-[#2AABEE] shadow-sm"
                  title="Start Date"
                />
                <span className="text-[#7E7870] font-medium">-</span>
                <input 
                  type="date" 
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="px-3 py-2 border border-[#E5E2DC] rounded-xl text-sm bg-white text-[#1F1C18] focus:outline-none focus:ring-2 focus:ring-[#2AABEE] shadow-sm"
                  title="End Date"
                />
              </div>
              {/* Search Bar */}
              <div className="relative group">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#7E7870] group-focus-within:text-[#2AABEE] transition-colors" />
                <input 
                  type="text" 
                  placeholder="Search name, category, amount..." 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 pr-4 py-2 w-full sm:w-48 sm:focus:w-64 transition-all duration-300 border border-[#E5E2DC] rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#2AABEE] focus:border-transparent bg-white text-[#1F1C18]"
                />
              </div>

              {/* Animated Custom Dropdown */}
              <div className="flex items-center gap-2 relative">
                <Filter size={16} className="text-[#7E7870] hidden sm:block" />
                <div className="relative">
                  <button 
                    onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                    onBlur={() => setTimeout(() => setIsDropdownOpen(false), 200)}
                    className="flex items-center justify-between gap-2 pl-4 pr-3 py-2 border border-[#E5E2DC] rounded-xl text-sm bg-white hover:bg-[#F3F1ED] transition-all duration-200 w-40 shadow-sm focus:outline-none focus:ring-2 focus:ring-[#2AABEE]"
                  >
                    <span className="capitalize font-medium text-[#1F1C18] truncate">
                      {filterType === 'all' ? 'All Categories' : filterType}
                    </span>
                    <svg className={`w-4 h-4 text-[#7E7870] transition-transform duration-300 ${isDropdownOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
                    </svg>
                  </button>
                  
                  {/* Dropdown Menu */}
                  <div className={`absolute right-0 mt-2 w-48 bg-white border border-[#E5E2DC] rounded-xl shadow-[0_10px_25px_-5px_rgba(0,0,0,0.1)] z-20 origin-top-right transition-all duration-200 ${isDropdownOpen ? 'opacity-100 scale-100 translate-y-0' : 'opacity-0 scale-95 -translate-y-2 pointer-events-none'}`}>
                    <div className="py-2">
                      {['all', 'expense', 'income', 'lent', 'borrowed'].map(f => (
                        <button
                          key={f}
                          onClick={() => { setFilterType(f); setIsDropdownOpen(false); }}
                          className={`w-full text-left px-4 py-2.5 text-sm capitalize transition-colors ${filterType === f ? 'bg-[#2AABEE]/10 text-[#2AABEE] font-semibold border-l-2 border-[#2AABEE]' : 'text-[#7E7870] hover:bg-[#F3F1ED] border-l-2 border-transparent'}`}
                        >
                          {f === 'all' ? 'All Categories' : f}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Animated Sort Dropdown */}
              <div className="flex items-center gap-2 relative">
                <div className="relative">
                  <button 
                    onClick={() => setIsSortDropdownOpen(!isSortDropdownOpen)}
                    onBlur={() => setTimeout(() => setIsSortDropdownOpen(false), 200)}
                    className="flex items-center justify-between gap-2 pl-4 pr-3 py-2 border border-[#E5E2DC] rounded-xl text-sm bg-white hover:bg-[#F3F1ED] transition-all duration-200 w-36 shadow-sm focus:outline-none focus:ring-2 focus:ring-[#2AABEE]"
                  >
                    <span className="font-medium text-[#1F1C18] truncate">
                      {sortType === 'date_desc' ? 'Newest First' : sortType === 'date_asc' ? 'Oldest First' : sortType === 'amount_desc' ? 'Highest Amt' : 'Lowest Amt'}
                    </span>
                    <svg className={`w-4 h-4 text-[#7E7870] transition-transform duration-300 ${isSortDropdownOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
                    </svg>
                  </button>
                  
                  {/* Sort Dropdown Menu */}
                  <div className={`absolute right-0 mt-2 w-40 bg-white border border-[#E5E2DC] rounded-xl shadow-[0_10px_25px_-5px_rgba(0,0,0,0.1)] z-20 origin-top-right transition-all duration-200 ${isSortDropdownOpen ? 'opacity-100 scale-100 translate-y-0' : 'opacity-0 scale-95 -translate-y-2 pointer-events-none'}`}>
                    <div className="py-2">
                      {[
                        { id: 'date_desc', label: 'Newest First' },
                        { id: 'date_asc', label: 'Oldest First' },
                        { id: 'amount_desc', label: 'Highest Amount' },
                        { id: 'amount_asc', label: 'Lowest Amount' }
                      ].map(s => (
                        <button
                          key={s.id}
                          onClick={() => { setSortType(s.id); setIsSortDropdownOpen(false); }}
                          className={`w-full text-left px-4 py-2.5 text-sm transition-colors ${sortType === s.id ? 'bg-[#2AABEE]/10 text-[#2AABEE] font-semibold border-l-2 border-[#2AABEE]' : 'text-[#7E7870] hover:bg-[#F3F1ED] border-l-2 border-transparent'}`}
                        >
                          {s.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="divide-y divide-[#E5E2DC]">
            {sortedTxs.map(tx => (
              <div key={tx.id} className="p-4 sm:px-6 flex items-center justify-between hover:bg-[#F3F1ED]/50 transition-colors">
                <div>
                  <div className="font-semibold text-[#1F1C18]">{tx.category} {tx.person ? `· ${tx.person}` : ''}</div>
                  <div className="text-sm text-[#7E7870] mt-1 capitalize">{tx.type} · {new Date(tx.created_at).toLocaleString()} {tx.note ? `· ${tx.note}` : ''}</div>
                </div>
                <div className={`font-bold text-lg ${['income','borrowed','settle_received'].includes(tx.type) ? 'text-emerald-600' : 'text-[#1F1C18]'}`}>
                  {['income','borrowed','settle_received'].includes(tx.type) ? '+' : '-'}₹{tx.amount}
                </div>
              </div>
            ))}
            {filteredTxs.length === 0 && <div className="p-8 text-center text-[#7E7870] flex flex-col items-center gap-2">
              <Search size={24} className="text-[#E5E2DC]" />
              <span>No transactions found.</span>
            </div>}
          </div>
        </div>

      </div>
    </div>
  )
}
