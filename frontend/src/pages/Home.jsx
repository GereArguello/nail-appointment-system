import { Header } from '../components/Header'
import { Hero } from '../components/Hero'
import { Gallery } from '../components/Gallery'
import { Services } from '../components/Services'
import { WorkingCalendar } from '../components/WorkingCalendar'


const business = {
  name: "Nail Studio",
  description: "Realzamos la belleza de tus uñas con diseños únicos.",
};

const images = [
  { id: 1, serviceId: 1, url: "/public/images/nails-1.jpg" },
  { id: 2, serviceId: 1, url: "/public/images/nails-2.jpg" },
  { id: 3, serviceId: 2, url: "/public/images/nails-3.jpg" },
  { id: 4, serviceId: 2, url: "/public/images/nails-4.jpg" },
  { id: 5, serviceId: 3, url: "/public/images/nails-5.jpg" },
];

const coverImages = images.filter(
  (image, index, array) =>
    array.findIndex(
      (item) => item.serviceId === image.serviceId
    ) === index
);

function Home() {
  return (
    <>
      <Header businessName={business.name} />

      <main>
        <Hero
          businessName={business.name}
          description={business.description}
        />

        <Gallery coverImages={coverImages} />

        <div className="home-content">
          <Services />
          <WorkingCalendar />
        </div>
      </main>
    </>
  );
}

export { Home };
