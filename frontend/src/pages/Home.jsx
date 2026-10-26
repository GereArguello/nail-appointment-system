import { Header } from '../components/Header'
import { Gallery } from '../components/Gallery'
import { Services } from '../components/Services'
import { WorkingCalendar } from '../components/WorkingCalendar'


function Home() {
  return (
    <>
      <Header />

      <main>
        <Gallery />
        <Services />
        <WorkingCalendar />
      </main>
    </>
  );
}

export { Home };
