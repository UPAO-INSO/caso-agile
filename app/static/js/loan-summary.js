const form = document.querySelector('#loan-form');
const summaryContainer = document.querySelector('[data-summary]');
const emptyState = summaryContainer?.querySelector('[data-summary-empty]');
const contentState = summaryContainer?.querySelector('[data-summary-content]');
const totalsTotal = summaryContainer?.querySelector('[data-summary-total]');
const totalsMonthly = summaryContainer?.querySelector('[data-summary-monthly]');
const installmentsLabel = summaryContainer?.querySelector(
  '[data-summary-installments-label]'
);
const scheduleTitle = summaryContainer?.querySelector(
  '[data-summary-schedule-title]'
);
const scheduleList = summaryContainer?.querySelector('[data-summary-schedule]');
const submitButton = summaryContainer?.querySelector('.primary-button');
const navbarDateValue = document.querySelector('[data-current-date-value]');

const formatCurrency = (value) =>
  new Intl.NumberFormat('es-PE', {
    style: 'currency',
    currency: 'PEN',
    minimumFractionDigits: 2,
  }).format(value || 0);

const allInputsFilled = (values) =>
  Object.values(values).every((val) =>
    typeof val === 'string' ? val.trim() !== '' : Number(val) > 0
  );

const calculateMonthlyPayment = (amount, installments, rate = 0) => {
  if (!installments) return 0;
  if (rate <= 0) return amount / installments;

  const monthlyRate = rate / 12;
  const factor = Math.pow(1 + monthlyRate, installments);
  return amount * ((monthlyRate * factor) / (factor - 1));
};

const generateSchedule = (values) => {
  const { installments, monthlyAmount } = values;
  const today = new Date();
  const baseDate = new Date(
    today.getFullYear(),
    today.getMonth(),
    today.getDate()
  );

  return Array.from({ length: installments }, (_, index) => {
    const dueDate = new Date(baseDate);
    dueDate.setMonth(dueDate.getMonth() + index + 1);

    const formatter = new Intl.DateTimeFormat('es-PE', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
    });

    return {
      label: `Cuota ${index + 1}`,
      dueDate: formatter.format(dueDate),
      amount: formatCurrency(monthlyAmount),
    };
  });
};

const renderSchedule = (items = []) => {
  if (!scheduleList) return;
  scheduleList.innerHTML = '';

  const fragment = document.createDocumentFragment();

  items.forEach((item, index) => {
    const li = document.createElement('li');
    const wrapper = document.createElement('div');
    wrapper.className = 'installment';
    wrapper.dataset.state = 'new';

    const indexSpan = document.createElement('span');
    indexSpan.className = 'installment__index';
    indexSpan.textContent = index + 1;

    const details = document.createElement('div');
    details.className = 'installment__details';

    const label = document.createElement('p');
    label.className = 'installment__label';
    label.textContent = item.label;

    const date = document.createElement('p');
    date.className = 'installment__date';
    date.textContent = item.dueDate;

    const amount = document.createElement('p');
    amount.className = 'installment__amount';
    amount.textContent = item.amount;

    details.append(label, date);
    wrapper.append(indexSpan, details, amount);
    li.append(wrapper);
    fragment.append(li);
  });

  scheduleList.append(fragment);
};

const updateSummary = (values) => {
  if (!summaryContainer || !emptyState || !contentState) return;

  const ready = allInputsFilled(values);

  emptyState.style.display = ready ? 'none' : '';
  contentState.classList.toggle('is-hidden', !ready);
  submitButton?.toggleAttribute('disabled', !ready);

  if (!ready) {
    scheduleList && (scheduleList.innerHTML = '');
    totalsTotal && (totalsTotal.innerHTML = 'S/ 0.00 <span class="currency">PEN</span>');
    totalsMonthly && (totalsMonthly.textContent = 'S/ 0.00');
    installmentsLabel && (installmentsLabel.textContent = 'Cuota Mensual');
    scheduleTitle && (scheduleTitle.textContent = 'Cronograma de Pagos');
    return;
  }

  const monthlyAmount = calculateMonthlyPayment(values.amount, values.installments);
  const scheduleItems = generateSchedule({
    installments: values.installments,
    monthlyAmount,
  });
  const totalAmount = monthlyAmount * values.installments;

  totalsTotal &&
    (totalsTotal.innerHTML = `${formatCurrency(totalAmount)} <span class="currency">PEN</span>`);
  totalsMonthly && (totalsMonthly.textContent = formatCurrency(monthlyAmount));
  installmentsLabel &&
    (installmentsLabel.textContent = `Cuota Mensual (${values.installments} cuotas)`);
  scheduleTitle &&
    (scheduleTitle.textContent = `Cronograma de Pagos (${values.installments} cuotas)`);

  renderSchedule(scheduleItems);
};

const handleInputChange = () => {
  const values = {
    dni: form?.dni.value ?? '',
    name: form?.nombre.value ?? '',
    amount: Number(form?.monto.value ?? 0),
    installments: Number(form?.cuotas.value ?? 0),
  };

  updateSummary(values);
};

const init = () => {
  const today = new Date();
  if (navbarDateValue) {
    navbarDateValue.textContent = new Intl.DateTimeFormat('es-PE', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
    }).format(today);
  }

  if (form) {
    updateSummary({ dni: '', name: '', amount: 0, installments: 0 });
    form.addEventListener('input', handleInputChange);
  }
};

init();
